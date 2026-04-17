"""HDBSCAN + UMAP cluster loops.

Three cadences run as background asyncio tasks:

* ``run_clusterer_daily``   — every 60 s over a 24 h window
* ``run_clusterer_weekly``  — every 15 min over a 7 d window
* ``run_clusterer_monthly`` — every 1 h over a 30 d window

Each queries DuckDB for recently-edited articles with embeddings, runs
HDBSCAN clustering, projects to 2-D via UMAP (Procrustes-aligned to the
previous run), computes c-TF-IDF labels, and writes results to Supabase
(``cluster_snapshots`` + ``cluster_members``).
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from functools import partial

import hdbscan
import numpy as np

from . import config, storage
from .labels import ctfidf_labels
from .state import state
from .umap_state import UmapState

log = logging.getLogger(__name__)


# ------------------------------------------------------------------
# CPU-bound helpers (run in thread executor)
# ------------------------------------------------------------------

def _do_hdbscan(
    embeddings: np.ndarray,
    min_cluster_size: int,
    selection: str = "eom",
) -> np.ndarray:
    """Fit HDBSCAN and return cluster labels (-1 = noise)."""
    clusterer = hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        metric="euclidean",
        cluster_selection_method=selection,
    )
    return clusterer.fit_predict(embeddings)


def _do_umap(umap_st: UmapState, embeddings: np.ndarray) -> np.ndarray:
    """Fit or transform UMAP, returning (N, 2) coordinates."""
    if umap_st._reducer is None:
        return umap_st.fit_initial(embeddings)
    return umap_st.transform(embeddings)


# ------------------------------------------------------------------
# Core pipeline
# ------------------------------------------------------------------

async def _run_cluster_pipeline(period: str, lookback_hours: int) -> None:
    """Cluster articles edited within *lookback_hours* and write to Supabase."""
    if state.db is None:
        return

    loop = asyncio.get_running_loop()

    # ---- 1. Query DuckDB (offloaded to avoid blocking event loop) --------
    # Stratified sampling: head slice preserves high-signal popular topics,
    # tail slice adds diversity so HDBSCAN has mid-frequency clusters to latch
    # onto. Falls back to pure top-N if STRATIFIED_TAIL_FRACTION is 0.
    max_articles = config.MAX_CLUSTER_ARTICLES
    tail_fraction = max(0.0, min(0.9, config.STRATIFIED_TAIL_FRACTION))
    head_limit = int(max_articles * (1.0 - tail_fraction))
    tail_limit = max_articles - head_limit
    tail_pool_size = int(max_articles * config.STRATIFIED_TAIL_POOL_MULT)

    def _query_db():
        if tail_limit <= 0 or tail_fraction <= 0:
            return state.db.execute(
                f"""
                SELECT a.title, a.summary, a.embedding,
                       COALESCE(SUM(eb.edit_count), 0) AS total_edits
                FROM articles a
                INNER JOIN edit_buckets eb ON eb.title = a.title
                WHERE eb.hour_bucket > now() - INTERVAL '{lookback_hours} HOURS'
                  AND a.embedding IS NOT NULL
                GROUP BY a.title, a.summary, a.embedding
                ORDER BY total_edits DESC
                LIMIT {max_articles}
                """
            ).fetchall()
        # Stratified: head (top N by edits) UNION tail (random sample from
        # articles ranked head_limit+1 .. tail_pool_size)
        return state.db.execute(
            f"""
            WITH joined AS (
                SELECT a.title, a.summary, a.embedding,
                       COALESCE(SUM(eb.edit_count), 0) AS total_edits
                FROM articles a
                INNER JOIN edit_buckets eb ON eb.title = a.title
                WHERE eb.hour_bucket > now() - INTERVAL '{lookback_hours} HOURS'
                  AND a.embedding IS NOT NULL
                GROUP BY a.title, a.summary, a.embedding
            ),
            ranked AS (
                SELECT *, ROW_NUMBER() OVER (ORDER BY total_edits DESC) AS rnk
                FROM joined
            ),
            head AS (
                SELECT title, summary, embedding, total_edits
                FROM ranked WHERE rnk <= {head_limit}
            ),
            tail AS (
                SELECT title, summary, embedding, total_edits
                FROM ranked
                WHERE rnk > {head_limit} AND rnk <= {tail_pool_size}
                ORDER BY random()
                LIMIT {tail_limit}
            )
            SELECT * FROM head
            UNION ALL
            SELECT * FROM tail
            """
        ).fetchall()

    try:
        rows = await loop.run_in_executor(None, _query_db)
    except Exception:
        log.exception("clusterer[%s]: duckdb query failed", period)
        return

    if not rows:
        log.debug("clusterer[%s]: no articles in window", period)
        return

    titles = [r[0] for r in rows]
    summaries = [r[1] or "" for r in rows]
    embeddings = np.array([list(r[2]) for r in rows], dtype=np.float64)
    edit_counts = {r[0]: int(r[3]) for r in rows}
    n = len(titles)

    # ---- 2. Early exit ---------------------------------------------------
    if n < config.MIN_CLUSTER_SIZE:
        log.info("clusterer[%s]: only %d articles (< %d), skipping", period, n, config.MIN_CLUSTER_SIZE)
        return

    # ---- 3. HDBSCAN (offloaded) -----------------------------------------
    params = config.HDBSCAN_PARAMS.get(period, {"min_cluster_size": config.MIN_CLUSTER_SIZE, "selection": "eom"})
    labels = await loop.run_in_executor(
        None,
        partial(_do_hdbscan, embeddings, params["min_cluster_size"], params["selection"]),
    )

    valid_clusters = set(labels) - {-1}
    if not valid_clusters:
        log.info(
            "clusterer[%s]: all %d articles are noise (min_size=%d, selection=%s), skipping",
            period, n, params["min_cluster_size"], params["selection"],
        )
        return

    # ---- 4. UMAP (offloaded) --------------------------------------------
    umap_path = f"{config.DATA_DIR}/umap_{period}.pkl"
    umap_st = UmapState()
    umap_st.load(umap_path)

    coords_2d = await loop.run_in_executor(
        None, partial(_do_umap, umap_st, embeddings)
    )
    coords_2d = umap_st.align_to_previous(coords_2d, titles)
    umap_st.save(umap_path)

    # ---- 5. c-TF-IDF labels ---------------------------------------------
    docs_by_cluster: dict[int, list[str]] = {}
    for i, cid in enumerate(labels):
        if cid == -1:
            continue
        cid = int(cid)
        docs_by_cluster.setdefault(cid, []).append(summaries[i])

    cluster_terms = ctfidf_labels(docs_by_cluster, top_n=5)

    # ---- 6. Per-cluster metadata -----------------------------------------
    cluster_meta: dict[int, dict] = {}
    for cid in valid_clusters:
        cid = int(cid)
        member_idx = [i for i in range(n) if int(labels[i]) == cid]
        size = len(member_idx)

        # Representative titles (closest to centroid)
        cluster_embs = embeddings[member_idx]
        centroid = cluster_embs.mean(axis=0)
        centroid_norm = centroid / (np.linalg.norm(centroid) + 1e-9)
        emb_norms = cluster_embs / (np.linalg.norm(cluster_embs, axis=1, keepdims=True) + 1e-9)
        cosine_sims = emb_norms @ centroid_norm
        top_k = min(5, size)
        rep_idx = cosine_sims.argsort()[::-1][:top_k]
        rep_titles = [titles[member_idx[j]] for j in rep_idx]

        # Terms and label — use most representative title as label
        terms = cluster_terms.get(cid, [])
        # Primary: best rep title; fallback to 2nd if first is too short
        if len(rep_titles) >= 2 and len(rep_titles[0]) < 6:
            label = rep_titles[1]
        elif rep_titles:
            label = rep_titles[0]
        elif terms:
            label = " · ".join(terms[:3])
        else:
            label = f"Cluster {cid}"

        # Momentum: mean edits per hour across members
        total_member_edits = sum(edit_counts.get(titles[i], 0) for i in member_idx)
        momentum = total_member_edits / max(lookback_hours, 1) / max(size, 1)

        # Centroid in UMAP space
        cx = float(coords_2d[member_idx, 0].mean())
        cy = float(coords_2d[member_idx, 1].mean())

        cluster_meta[cid] = {
            "label": label,
            "size": size,
            "rep_titles": rep_titles,
            "top_terms": terms,
            "momentum": round(momentum, 4),
            "centroid_x": round(cx, 4),
            "centroid_y": round(cy, 4),
        }

    # ---- 7. period_start -------------------------------------------------
    now = datetime.now(timezone.utc)
    if period == "day":
        period_start = now.date()
    elif period == "week":
        period_start = (now - timedelta(days=now.weekday())).date()
    else:  # month
        period_start = now.date().replace(day=1)

    # ---- 8. Write to Supabase --------------------------------------------
    sb = storage.get_supabase()
    if sb is None:
        log.warning("clusterer[%s]: supabase unavailable, skipping write", period)
        return

    try:
        ps = str(period_start)

        # Build the new rows FIRST, write them BEFORE deleting obsolete ones.
        # This closes the tiny window where the frontend could observe an empty
        # snapshot between the old DELETE and the new INSERT.
        snapshot_rows = [
            {
                "period": period,
                "period_start": ps,
                "cluster_id": cid,
                "label": meta["label"],
                "size": meta["size"],
                "rep_titles": meta["rep_titles"],
                "top_terms": meta["top_terms"],
                "momentum": meta["momentum"],
                "centroid_x": meta["centroid_x"],
                "centroid_y": meta["centroid_y"],
            }
            for cid, meta in cluster_meta.items()
        ]
        new_cluster_ids = [int(cid) for cid in cluster_meta.keys()]
        new_titles = [titles[i] for i in range(n) if int(labels[i]) != -1]

        member_rows = []
        for i in range(n):
            cid = int(labels[i])
            if cid == -1:
                continue
            member_rows.append({
                "period": period,
                "period_start": ps,
                "title": titles[i],
                "cluster_id": cid,
                "umap_x": round(float(coords_2d[i, 0]), 4),
                "umap_y": round(float(coords_2d[i, 1]), 4),
                "edit_count": edit_counts.get(titles[i], 0),
            })

        # ── write new snapshot rows (upsert replaces same (period,period_start,cluster_id)) ──
        if snapshot_rows:
            sb.table("cluster_snapshots").upsert(snapshot_rows).execute()

        # ── write new member rows (batched) ──
        for i in range(0, len(member_rows), 500):
            sb.table("cluster_members").upsert(member_rows[i : i + 500]).execute()

        # ── now prune obsolete rows for this (period, period_start) ──
        # Any snapshot row whose cluster_id is NOT in the freshly-written set
        # is stale from a previous run and must go. Same for members whose title
        # is no longer in any cluster.
        try:
            if new_cluster_ids:
                sb.table("cluster_snapshots").delete().eq("period", period).eq("period_start", ps).not_.in_("cluster_id", new_cluster_ids).execute()
            else:
                sb.table("cluster_snapshots").delete().eq("period", period).eq("period_start", ps).execute()

            if new_titles:
                # Chunk the NOT IN filter — Supabase URL length is bounded
                chunk = 200
                existing_titles_res = sb.table("cluster_members").select("title").eq("period", period).eq("period_start", ps).execute()
                existing = {r["title"] for r in (existing_titles_res.data or [])}
                obsolete = list(existing - set(new_titles))
                for j in range(0, len(obsolete), chunk):
                    sb.table("cluster_members").delete().eq("period", period).eq("period_start", ps).in_("title", obsolete[j : j + chunk]).execute()
            else:
                sb.table("cluster_members").delete().eq("period", period).eq("period_start", ps).execute()
        except Exception:
            log.exception("clusterer[%s]: obsolete-row prune failed (non-fatal)", period)

    except Exception:
        log.exception("clusterer[%s]: supabase write failed", period)
        return

    noise_count = int((labels == -1).sum())
    log.info(
        "clusterer[%s]: %d articles -> %d clusters (%d noise), wrote to supabase",
        period, n, len(valid_clusters), noise_count,
    )


# ------------------------------------------------------------------
# Async loop wrappers
# ------------------------------------------------------------------

async def run_clusterer_daily() -> None:
    await asyncio.sleep(90)  # let embedder warm up
    while True:
        try:
            await _run_cluster_pipeline("day", lookback_hours=24)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("clusterer[day]: pipeline failed")
        await asyncio.sleep(60)


async def run_clusterer_weekly() -> None:
    await asyncio.sleep(120)
    while True:
        try:
            await _run_cluster_pipeline("week", lookback_hours=168)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("clusterer[week]: pipeline failed")
        await asyncio.sleep(900)


async def run_clusterer_monthly() -> None:
    await asyncio.sleep(180)
    while True:
        try:
            await _run_cluster_pipeline("month", lookback_hours=720)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("clusterer[month]: pipeline failed")
        await asyncio.sleep(3600)


# ------------------------------------------------------------------
# Eviction (32-day retention) + Monthly archive
# ------------------------------------------------------------------

_RETENTION_DAYS = 32
_last_archived_month: str | None = None


async def run_eviction() -> None:
    """Daily job: evict data older than 32 days, archive monthly snapshot."""
    global _last_archived_month
    await asyncio.sleep(300)  # let everything else stabilize
    while True:
        try:
            loop = asyncio.get_running_loop()
            now = datetime.now(timezone.utc)

            # ── 1. Archive monthly snapshot on month change ──────────
            current_month = now.strftime("%Y-%m")
            prev_month = (now.replace(day=1) - timedelta(days=1)).strftime("%Y-%m")

            if _last_archived_month != prev_month:
                # Check if we already archived this month in Supabase
                sb = storage.get_supabase()
                if sb is not None:
                    existing = (
                        sb.table("monthly_archives")
                        .select("year_month")
                        .eq("year_month", prev_month)
                        .limit(1)
                        .execute()
                    )
                    if not existing.data:
                        # Fetch the latest monthly snapshot
                        snap = (
                            sb.table("cluster_snapshots")
                            .select("*")
                            .eq("period", "month")
                            .order("period_start", desc=True)
                            .limit(50)
                            .execute()
                        )
                        if snap.data:
                            latest_start = snap.data[0]["period_start"]
                            month_clusters = [r for r in snap.data if r["period_start"] == latest_start]

                            archive_rows = [
                                {
                                    "year_month": prev_month,
                                    "cluster_id": c["cluster_id"],
                                    "label": c["label"],
                                    "size": c["size"],
                                    "rep_titles": c["rep_titles"],
                                    "top_terms": c["top_terms"],
                                    "momentum": c.get("momentum"),
                                    "centroid_x": c.get("centroid_x"),
                                    "centroid_y": c.get("centroid_y"),
                                    "total_articles": sum(r["size"] for r in month_clusters),
                                    "total_noise": 0,  # not tracked in snapshot
                                }
                                for c in month_clusters
                            ]
                            sb.table("monthly_archives").upsert(archive_rows).execute()
                            log.info("eviction: archived %d clusters for %s", len(archive_rows), prev_month)

                _last_archived_month = prev_month

            # ── 2. Evict old DuckDB data ─────────────────────────────
            if state.db is not None:
                def _evict():
                    state.db.execute(
                        f"DELETE FROM edit_buckets WHERE hour_bucket < now() - INTERVAL '{_RETENTION_DAYS} DAYS'"
                    )
                    deleted_buckets = state.db.execute("SELECT changes()").fetchone()[0]

                    state.db.execute(
                        f"""
                        DELETE FROM articles
                        WHERE title NOT IN (
                            SELECT DISTINCT title FROM edit_buckets
                        )
                        AND last_edited < now() - INTERVAL '{_RETENTION_DAYS} DAYS'
                        """
                    )
                    deleted_articles = state.db.execute("SELECT changes()").fetchone()[0]
                    return deleted_buckets, deleted_articles

                try:
                    db, da = await loop.run_in_executor(None, _evict)
                    if db > 0 or da > 0:
                        log.info("eviction: deleted %d edit_buckets, %d articles (>%dd)", db, da, _RETENTION_DAYS)
                except Exception:
                    log.exception("eviction: duckdb cleanup failed")

        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("eviction: job failed")

        # Run once per day (24h)
        await asyncio.sleep(86400)
