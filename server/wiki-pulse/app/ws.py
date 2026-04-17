"""WebSocket endpoint with ConnectionManager and background poll loop.

Streams live pipeline stats and cluster snapshots to connected clients.
Clients can subscribe to different time periods (day/week/month).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from . import storage
from .state import state

router = APIRouter()
log = logging.getLogger(__name__)

VALID_PERIODS = {"day", "week", "month"}
SUBSCRIBE_COOLDOWN = 1.0  # seconds between subscribe messages per client


# ------------------------------------------------------------------
# Connection manager
# ------------------------------------------------------------------

class ConnectionManager:
    """Track connected WebSocket clients and their subscribed periods."""

    def __init__(self) -> None:
        # client_id -> (websocket, period, last_subscribe_time)
        self.active: dict[str, tuple[WebSocket, str, float]] = {}

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        cid = uuid.uuid4().hex[:12]
        self.active[cid] = (ws, "day", 0.0)
        log.info("ws: client %s connected (%d total)", cid, len(self.active))
        return cid

    def disconnect(self, cid: str) -> None:
        self.active.pop(cid, None)
        log.info("ws: client %s disconnected (%d total)", cid, len(self.active))

    def set_period(self, cid: str, period: str) -> float:
        """Update client's period. Returns 0.0 on success, else seconds until cooldown clears."""
        entry = self.active.get(cid)
        if entry is None:
            return 0.0
        ws, _, last_sub = entry
        now = time.monotonic()
        remaining = SUBSCRIBE_COOLDOWN - (now - last_sub)
        if remaining > 0:
            return remaining
        self.active[cid] = (ws, period, now)
        return 0.0

    def get_period(self, cid: str) -> str:
        entry = self.active.get(cid)
        return entry[1] if entry else "day"

    async def send_to(self, cid: str, data: dict) -> None:
        entry = self.active.get(cid)
        if entry is None:
            return
        try:
            await entry[0].send_json(data)
        except Exception:
            self.disconnect(cid)

    async def broadcast_all(self, data: dict) -> None:
        stale: list[str] = []
        for cid, (ws, _, _) in self.active.items():
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(cid)
        for cid in stale:
            self.disconnect(cid)

    async def broadcast_to_period(self, period: str, data: dict) -> None:
        stale: list[str] = []
        for cid, (ws, p, _) in self.active.items():
            if p != period:
                continue
            try:
                await ws.send_json(data)
            except Exception:
                stale.append(cid)
        for cid in stale:
            self.disconnect(cid)

    def periods_with_clients(self) -> set[str]:
        return {p for _, (_, p, _) in self.active.items()}


manager = ConnectionManager()


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _compute_stats() -> dict:
    """Build stats dict from DuckDB (same logic as api.get_stats)."""
    active = 0
    embedded = 0
    if state.db is not None:
        try:
            row = state.db.execute(
                "SELECT count(DISTINCT title) FROM edit_buckets "
                "WHERE hour_bucket > now() - INTERVAL 24 HOUR"
            ).fetchone()
            active = int(row[0]) if row else 0
            row = state.db.execute("SELECT count(*) FROM articles").fetchone()
            embedded = int(row[0]) if row else 0
        except Exception:
            log.exception("ws: stats duckdb query failed")

    cluster_count = 0
    try:
        sb = storage.get_supabase()
        if sb is not None:
            res = (
                sb.table("cluster_snapshots")
                .select("period_start")
                .eq("period", "day")
                .order("period_start", desc=True)
                .limit(1)
                .execute()
            )
            if res.data:
                latest = res.data[0]["period_start"]
                cr = (
                    sb.table("cluster_snapshots")
                    .select("cluster_id", count="exact")
                    .eq("period", "day")
                    .eq("period_start", latest)
                    .execute()
                )
                cluster_count = cr.count if cr.count else len(cr.data)
    except Exception:
        log.exception("ws: stats supabase query failed")

    # Recent edits for the live edit rain visualization
    recent_edits = [
        {"title": e["title"], "ts": e.get("ts", 0)}
        for e in list(state.last_edits)[-15:]
    ]

    return {
        "edits_per_min": state.edits_per_min(),
        "active_articles": active,
        "embedded_articles": embedded,
        "cluster_count": cluster_count,
        "pending_embedding": len(state.needs_embedding),
        "recent_edits": recent_edits,
    }


def _fetch_cluster_activity(members: list[dict], lookback_hours: int = 24) -> dict:
    """Return hourly edit counts per cluster from DuckDB.

    Returns {cluster_id: [{hour: "HH:00", edits: N}, ...]} sorted by hour.
    """
    if state.db is None or not members:
        return {}

    title_to_cluster: dict[str, int] = {}
    for m in members:
        title_to_cluster[m["title"]] = m["cluster_id"]

    try:
        rows = state.db.execute(
            f"""
            SELECT eb.title, eb.hour_bucket, eb.edit_count
            FROM edit_buckets eb
            WHERE eb.hour_bucket > now() - INTERVAL '{lookback_hours} HOURS'
            """
        ).fetchall()
    except Exception:
        log.exception("ws: activity query failed")
        return {}

    from collections import defaultdict
    hourly: dict[int, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for title, hour_bucket, edit_count in rows:
        cid = title_to_cluster.get(title)
        if cid is not None:
            h = hour_bucket.strftime("%H:00") if hasattr(hour_bucket, "strftime") else str(hour_bucket)
            hourly[cid][h] += edit_count

    # Convert to sorted lists
    result = {}
    for cid, hours in hourly.items():
        sorted_hours = sorted(hours.items())
        result[cid] = [{"hour": h, "edits": c} for h, c in sorted_hours]
    return result


def _fetch_snapshot(period: str) -> dict | None:
    """Fetch latest snapshot + members for *period* from Supabase."""
    try:
        sb = storage.get_supabase()
        if sb is None:
            return None

        snap_res = (
            sb.table("cluster_snapshots")
            .select("cluster_id,label,size,rep_titles,top_terms,momentum,centroid_x,centroid_y,generated_at,period_start")
            .eq("period", period)
            .order("period_start", desc=True)
            .order("cluster_id")
            .limit(200)
            .execute()
        )
        if not snap_res.data:
            return {"period": period, "period_start": None, "clusters": [], "members": []}

        latest_start = snap_res.data[0]["period_start"]
        clusters = [r for r in snap_res.data if r["period_start"] == latest_start]

        mem_res = (
            sb.table("cluster_members")
            .select("title,cluster_id,umap_x,umap_y,edit_count")
            .eq("period", period)
            .eq("period_start", latest_start)
            .execute()
        )

        members_data = mem_res.data or []

        # Fetch hourly activity for heatmap/sparklines
        lookback = {"day": 24, "week": 168, "month": 720}.get(period, 24)
        activity = _fetch_cluster_activity(members_data, lookback_hours=min(lookback, 48))

        return {
            "period": period,
            "period_start": latest_start,
            "clusters": clusters,
            "members": members_data,
            "activity": activity,
        }
    except Exception:
        log.exception("ws: fetch snapshot failed for %s", period)
        return None


# ------------------------------------------------------------------
# Background poll loop
# ------------------------------------------------------------------

_last_seen: dict[str, str | None] = {"day": None, "week": None, "month": None}


async def run_ws_poll() -> None:
    """Poll stats and detect new snapshots every 30 s, broadcast to clients."""
    await asyncio.sleep(10)  # let other services warm up
    loop = asyncio.get_running_loop()
    while True:
        try:
            # Broadcast stats to everyone
            if manager.active:
                stats = await loop.run_in_executor(None, _compute_stats)
                await manager.broadcast_all({"type": "stats", **stats})

                # Check for new snapshots per active period
                for period in manager.periods_with_clients():
                    snap = await loop.run_in_executor(None, _fetch_snapshot, period)
                    if snap is None:
                        continue
                    ps = snap.get("period_start")
                    if ps and ps != _last_seen.get(period):
                        _last_seen[period] = ps
                        await manager.broadcast_to_period(
                            period,
                            {"type": "snapshot", **snap},
                        )
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("ws: poll loop error")

        await asyncio.sleep(30)


# ------------------------------------------------------------------
# WebSocket endpoint
# ------------------------------------------------------------------

@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    loop = asyncio.get_running_loop()
    cid = await manager.connect(websocket)
    try:
        # Send init payload — both helpers are sync I/O, offload so we don't block the loop
        period = manager.get_period(cid)
        stats = await loop.run_in_executor(None, _compute_stats)
        snap = await loop.run_in_executor(None, _fetch_snapshot, period) or {
            "period": period, "period_start": None, "clusters": [], "members": []
        }
        await manager.send_to(cid, {
            "type": "init",
            "period": period,
            "stats": stats,
            "snapshot": snap,
        })

        # Message loop
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                continue  # ignore non-JSON

            msg_type = msg.get("type") if isinstance(msg, dict) else None

            if msg_type == "subscribe":
                new_period = msg.get("period", "")
                if new_period not in VALID_PERIODS:
                    continue
                wait = manager.set_period(cid, new_period)
                if wait > 0:
                    # Tell the client exactly how long to wait before retrying
                    await manager.send_to(cid, {
                        "type": "error",
                        "code": "rate_limited",
                        "retry_after": round(wait, 2),
                        "period": new_period,
                    })
                    continue
                snap = await loop.run_in_executor(None, _fetch_snapshot, new_period) or {
                    "period": new_period, "period_start": None,
                    "clusters": [], "members": [],
                }
                await manager.send_to(cid, {"type": "snapshot", **snap})
            # Unknown types silently ignored

    except WebSocketDisconnect:
        pass
    except Exception:
        log.exception("ws: error for client %s", cid)
    finally:
        manager.disconnect(cid)
