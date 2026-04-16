"""Summary-fetch + MiniLM embedder.

Drains ``state.needs_embedding`` in batches of up to 200 titles every
30 s. For each title:

1. Fetch ``/api/rest_v1/page/summary/{title}`` with the Wikimedia UA
   header, at 10-wide concurrency.
2. Embed the ``title + extract`` with
   ``sentence-transformers/all-MiniLM-L6-v2`` on CPU (384-dim).
3. Upsert into DuckDB ``articles``.

Titles we've seen within the last 24 h are skipped via a lightweight
timestamp cache to avoid re-embedding the same article every hour.
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any
from urllib.parse import quote

import httpx

from . import config
from .state import state

log = logging.getLogger(__name__)

BATCH_SIZE = 200
CONCURRENCY = 10
CADENCE = 30.0
RECENT_TTL = 24 * 3600.0  # don't re-embed within 24 h

_model: Any = None
_recent: dict[str, float] = {}


def _get_model() -> Any:
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        log.info("embedder: loading all-MiniLM-L6-v2 (first call; ~80 MB)")
        _model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        log.info("embedder: model loaded")
    return _model


def _prune_recent(now: float) -> None:
    cutoff = now - RECENT_TTL
    stale = [k for k, v in _recent.items() if v < cutoff]
    for k in stale:
        _recent.pop(k, None)


async def _fetch_summary(
    client: httpx.AsyncClient, title: str, sem: asyncio.Semaphore
) -> tuple[str, str | None]:
    async with sem:
        url = config.WIKI_SUMMARY_URL.format(title=quote(title.replace(" ", "_"), safe=""))
        try:
            r = await client.get(url, timeout=15.0)
            if r.status_code != 200:
                return (title, None)
            data = r.json()
            extract = data.get("extract") or ""
            return (title, f"{title}. {extract}".strip())
        except Exception:
            return (title, None)


async def _embed_batch(titles: list[str]) -> None:
    if not titles:
        return
    headers = {"User-Agent": config.USER_AGENT, "Accept": "application/json"}
    sem = asyncio.Semaphore(CONCURRENCY)
    async with httpx.AsyncClient(headers=headers) as client:
        results = await asyncio.gather(
            *(_fetch_summary(client, t, sem) for t in titles)
        )

    docs: list[str] = []
    kept: list[str] = []
    for title, doc in results:
        if doc is None:
            # 404s, redirects, transient failures — drop from needs_embedding
            # so we don't spin on them; the next edit will re-queue.
            continue
        kept.append(title)
        docs.append(doc)

    if not docs:
        log.info("embedder: batch of %d yielded 0 usable summaries", len(titles))
        return

    model = _get_model()
    # sentence-transformers' encode is sync + CPU-bound — offload.
    loop = asyncio.get_running_loop()
    embeddings = await loop.run_in_executor(
        None,
        lambda: model.encode(
            docs,
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        ),
    )

    now_iso_expr = "now()"
    rows = []
    for title, doc, vec in zip(kept, docs, embeddings):
        # summary column stores just the extract, not the "title. extract" prefix
        summary = doc[len(title) + 2 :] if doc.startswith(f"{title}. ") else doc
        rows.append((title, summary, list(map(float, vec))))

    if state.db is None:
        log.warning("embedder: no duckdb connection; skipping upsert")
        return

    state.db.executemany(
        f"""
        INSERT INTO articles (title, summary, embedding, first_seen, last_edited)
        VALUES (?, ?, ?, {now_iso_expr}, {now_iso_expr})
        ON CONFLICT (title) DO UPDATE SET
            summary     = EXCLUDED.summary,
            embedding   = EXCLUDED.embedding,
            last_edited = EXCLUDED.last_edited
        """,
        rows,
    )
    now = time.time()
    for t in kept:
        _recent[t] = now
    log.info("embedder: upserted %d articles (skipped %d)", len(rows), len(titles) - len(rows))


async def run_embedder() -> None:
    # Let the stream warm up before first pass.
    await asyncio.sleep(15.0)
    while True:
        try:
            now = time.time()
            _prune_recent(now)
            pending = [
                t for t in list(state.needs_embedding) if _recent.get(t, 0.0) < now - RECENT_TTL
            ]
            # remove from set regardless — if the fetch fails, the next edit re-queues
            batch = pending[:BATCH_SIZE]
            for t in batch:
                state.needs_embedding.discard(t)

            if batch:
                log.info("embedder: batch of %d (queue remaining=%d)", len(batch), len(state.needs_embedding))
                await _embed_batch(batch)
            else:
                log.info("embedder: idle")
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            log.exception("embedder: batch failed")
        await asyncio.sleep(CADENCE)
