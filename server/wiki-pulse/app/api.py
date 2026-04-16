"""REST routes.

``/api/stats`` returns live pipeline metrics.
``/api/snapshot`` and ``/api/cluster`` serve cluster data from Supabase.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Query

from . import storage
from .state import state

router = APIRouter()
log = logging.getLogger(__name__)


@router.get("/api/stats")
async def get_stats():
    active = 0
    embedded = 0
    if state.db is not None:
        try:
            row = state.db.execute(
                """
                SELECT count(DISTINCT title)
                FROM edit_buckets
                WHERE hour_bucket > now() - INTERVAL 24 HOUR
                """
            ).fetchone()
            active = int(row[0]) if row else 0
            row = state.db.execute("SELECT count(*) FROM articles").fetchone()
            embedded = int(row[0]) if row else 0
        except Exception:
            log.exception("stats: duckdb query failed")

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
                latest_start = res.data[0]["period_start"]
                count_res = (
                    sb.table("cluster_snapshots")
                    .select("cluster_id", count="exact")
                    .eq("period", "day")
                    .eq("period_start", latest_start)
                    .execute()
                )
                cluster_count = count_res.count if count_res.count else len(count_res.data)
    except Exception:
        log.exception("stats: supabase cluster count query failed")

    return {
        "edits_per_min": state.edits_per_min(),
        "active_articles": active,
        "embedded_articles": embedded,
        "cluster_count": cluster_count,
        "pending_embedding": len(state.needs_embedding),
    }


@router.get("/api/snapshot")
async def get_snapshot(period: str = Query("day", pattern="^(day|week|month)$")):
    try:
        sb = storage.get_supabase()
        if sb is None:
            return {"period": period, "clusters": [], "error": "supabase_unavailable"}

        # Get latest period_start for this period
        res = (
            sb.table("cluster_snapshots")
            .select("*")
            .eq("period", period)
            .order("period_start", desc=True)
            .order("cluster_id")
            .limit(200)
            .execute()
        )
        if not res.data:
            return {"period": period, "clusters": []}

        latest_start = res.data[0]["period_start"]
        clusters = [row for row in res.data if row["period_start"] == latest_start]

        return {"period": period, "period_start": latest_start, "clusters": clusters}
    except Exception:
        log.exception("snapshot: query failed")
        return {"period": period, "clusters": [], "error": "query_failed"}


@router.get("/api/cluster/{period}/{cluster_id}")
async def get_cluster(period: str, cluster_id: int):
    try:
        sb = storage.get_supabase()
        if sb is None:
            return {"period": period, "id": cluster_id, "members": [], "error": "supabase_unavailable"}

        # Get the latest snapshot for this cluster
        snap_res = (
            sb.table("cluster_snapshots")
            .select("*")
            .eq("period", period)
            .eq("cluster_id", cluster_id)
            .order("period_start", desc=True)
            .limit(1)
            .execute()
        )
        if not snap_res.data:
            return {"period": period, "id": cluster_id, "members": [], "snapshot": None}

        snapshot = snap_res.data[0]
        period_start = snapshot["period_start"]

        # Get all members for this cluster
        mem_res = (
            sb.table("cluster_members")
            .select("*")
            .eq("period", period)
            .eq("period_start", period_start)
            .eq("cluster_id", cluster_id)
            .execute()
        )

        return {
            "period": period,
            "id": cluster_id,
            "snapshot": snapshot,
            "members": mem_res.data or [],
        }
    except Exception:
        log.exception("cluster detail: query failed")
        return {"period": period, "id": cluster_id, "members": [], "error": "query_failed"}
