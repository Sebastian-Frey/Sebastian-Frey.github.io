"""FastAPI entrypoint: wires the REST + WS routers and launches the
ingest/bucket/embed/cluster asyncio loops on startup.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import FastAPI

from . import api, bucketer, clusterer, embedder, ingestor, storage, ws
from .state import state

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
log = logging.getLogger("wikipulse")

app = FastAPI(title="Wiki Pulse")
app.include_router(api.router)
app.include_router(ws.router)

_tasks: list[asyncio.Task] = []


@app.on_event("startup")
async def _startup() -> None:
    try:
        state.db = storage.get_duckdb()
        storage.init_schema(state.db)
    except Exception:  # pragma: no cover
        log.exception("startup: duckdb init failed (continuing)")

    queue: asyncio.Queue = asyncio.Queue()
    _tasks.extend(
        [
            asyncio.create_task(ingestor.run_ingestor(queue), name="ingestor"),
            asyncio.create_task(bucketer.run_bucketer(queue), name="bucketer"),
            asyncio.create_task(embedder.run_embedder(), name="embedder"),
            asyncio.create_task(clusterer.run_clusterer_daily(), name="cluster-day"),
            asyncio.create_task(clusterer.run_clusterer_weekly(), name="cluster-week"),
            asyncio.create_task(clusterer.run_clusterer_monthly(), name="cluster-month"),
            asyncio.create_task(ws.run_ws_poll(), name="ws-poll"),
            asyncio.create_task(clusterer.run_eviction(), name="eviction"),
        ]
    )
    log.info("startup: %d background tasks launched", len(_tasks))


@app.on_event("shutdown")
async def _shutdown() -> None:
    for t in _tasks:
        t.cancel()
    for t in _tasks:
        try:
            await t
        except (asyncio.CancelledError, Exception):
            pass
    _tasks.clear()
    if state.db is not None:
        try:
            state.db.close()
        except Exception:
            pass
        state.db = None


@app.get("/")
async def root() -> dict:
    return {"service": "wiki-pulse", "status": "ok"}
