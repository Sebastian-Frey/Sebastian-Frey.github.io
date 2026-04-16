"""Drain the ingest queue into hourly DuckDB rollups.

Every ``DRAIN_INTERVAL`` seconds, pulls everything currently on the
asyncio queue, aggregates by ``(title, hour_bucket)`` in memory, and
upserts the result into ``edit_buckets``. Also feeds rolling stats
(``state.edits_per_min``) and the pending-embedding set consumed by the
embedder in phase 3.
"""
from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from .state import state

log = logging.getLogger(__name__)

DRAIN_INTERVAL = 30.0  # seconds


def _drain(queue: asyncio.Queue) -> list[dict[str, Any]]:
    batch: list[dict[str, Any]] = []
    while True:
        try:
            batch.append(queue.get_nowait())
        except asyncio.QueueEmpty:
            return batch


async def run_bucketer(queue: asyncio.Queue) -> None:
    while True:
        try:
            await asyncio.sleep(DRAIN_INTERVAL)
            batch = _drain(queue)
            if not batch:
                log.info(
                    "bucketer: idle (epm=%d pending_embed=%d)",
                    state.edits_per_min(),
                    len(state.needs_embedding),
                )
                continue

            agg: dict[tuple[str, datetime], dict[str, Any]] = defaultdict(
                lambda: {"count": 0, "bytes": 0, "users": set()}
            )
            for e in batch:
                ts = e["ts"]
                if not ts:
                    continue
                state.record_edit(ts)
                state.needs_embedding.add(e["title"])
                state.last_edits.append(
                    {"title": e["title"], "ts": ts, "comment": e["comment"]}
                )
                hour = datetime.fromtimestamp(ts, tz=timezone.utc).replace(
                    minute=0, second=0, microsecond=0
                )
                key = (e["title"], hour)
                agg[key]["count"] += 1
                agg[key]["bytes"] += e["byte_delta"]
                if e["user"]:
                    agg[key]["users"].add(e["user"])

            if state.db is not None and agg:
                rows = [
                    (t, h, v["count"], v["bytes"], len(v["users"]))
                    for (t, h), v in agg.items()
                ]
                state.db.executemany(
                    """
                    INSERT INTO edit_buckets
                        (title, hour_bucket, edit_count, byte_delta, editor_count)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT (title, hour_bucket) DO UPDATE SET
                        edit_count   = edit_buckets.edit_count + EXCLUDED.edit_count,
                        byte_delta   = edit_buckets.byte_delta + EXCLUDED.byte_delta,
                        editor_count = GREATEST(edit_buckets.editor_count, EXCLUDED.editor_count)
                    """,
                    rows,
                )

            log.info(
                "bucketer: flushed %d events → %d buckets (epm=%d pending_embed=%d)",
                len(batch),
                len(agg),
                state.edits_per_min(),
                len(state.needs_embedding),
            )
        except asyncio.CancelledError:
            raise
        except Exception:  # pragma: no cover
            log.exception("bucketer: flush failed")
