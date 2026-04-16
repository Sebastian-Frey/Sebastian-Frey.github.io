"""Wikimedia recent-change SSE ingestor.

Opens the public ``recentchange`` stream, filters to English Wikipedia
mainspace edits by non-bots, and pushes lightweight event dicts onto the
shared asyncio queue for the bucketer to drain. Reconnects with
exponential backoff on any transport error.
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

import httpx
from httpx_sse import aconnect_sse

from . import config

log = logging.getLogger(__name__)


def _filter(ev: dict[str, Any]) -> bool:
    if ev.get("wiki") != "enwiki":
        return False
    if ev.get("namespace") != 0:
        return False
    if ev.get("bot"):
        return False
    if ev.get("type") not in ("edit", "new"):
        return False
    if not ev.get("title"):
        return False
    return True


def _normalize(ev: dict[str, Any]) -> dict[str, Any]:
    length = ev.get("length") or {}
    new = length.get("new") or 0
    old = length.get("old") or 0
    return {
        "title": ev["title"],
        "ts": float(ev.get("timestamp") or 0),
        "byte_delta": int(new) - int(old),
        "user": ev.get("user") or "",
        "comment": ev.get("comment") or "",
        "type": ev["type"],
    }


async def run_ingestor(queue: asyncio.Queue) -> None:
    backoff = 1.0
    headers = {
        "User-Agent": config.USER_AGENT,
        "Accept": "text/event-stream",
    }
    while True:
        try:
            async with httpx.AsyncClient(timeout=None, headers=headers) as client:
                async with aconnect_sse(client, "GET", config.WIKI_SSE_URL) as es:
                    log.info("ingestor: connected to %s", config.WIKI_SSE_URL)
                    backoff = 1.0
                    async for sse in es.aiter_sse():
                        if sse.event != "message" or not sse.data:
                            continue
                        try:
                            ev = json.loads(sse.data)
                        except json.JSONDecodeError:
                            continue
                        if not _filter(ev):
                            continue
                        await queue.put(_normalize(ev))
        except asyncio.CancelledError:
            log.info("ingestor: cancelled")
            raise
        except Exception as e:  # pragma: no cover — network noise
            log.warning("ingestor: disconnected (%s); retry in %.1fs", e, backoff)
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 60.0)
