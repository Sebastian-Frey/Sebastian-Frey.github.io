"""Procrustes-aligned UMAP cache.

Keeps the 2-D projection stable day-over-day: a new UMAP is fit once a
week and the daily transforms are Procrustes-aligned to the previous
day's coordinates so clusters don't visually jump around.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

import joblib
import numpy as np
import umap

log = logging.getLogger(__name__)


class UmapState:
    """Persistent UMAP reducer with Procrustes alignment between runs."""

    def __init__(self) -> None:
        self._reducer: umap.UMAP | None = None
        self._prev_coords: np.ndarray | None = None
        self._prev_titles: list[str] | None = None

    # ------------------------------------------------------------------
    # Fitting / transforming
    # ------------------------------------------------------------------

    def fit_initial(self, X: np.ndarray) -> np.ndarray:
        """Fit a fresh UMAP reducer and return 2-D coordinates."""
        self._reducer = umap.UMAP(
            n_components=2,
            n_neighbors=15,
            min_dist=0.1,
            metric="cosine",
            random_state=42,
        )
        coords = self._reducer.fit_transform(X)
        return coords

    def transform(self, X: np.ndarray) -> np.ndarray:
        """Project *X* with the existing reducer, or fit a new one."""
        if self._reducer is None:
            return self.fit_initial(X)
        try:
            return self._reducer.transform(X)
        except Exception:
            log.warning("umap: transform failed, falling back to fit_initial")
            return self.fit_initial(X)

    # ------------------------------------------------------------------
    # Procrustes alignment
    # ------------------------------------------------------------------

    def align_to_previous(
        self, coords: np.ndarray, titles: list[str]
    ) -> np.ndarray:
        """Rotate/scale *coords* to best match the previous run's layout.

        Uses SVD-based Procrustes on the overlapping title set.  If fewer
        than 3 titles overlap, alignment is skipped.
        """
        if self._prev_coords is None or self._prev_titles is None:
            self._prev_coords = coords.copy()
            self._prev_titles = list(titles)
            return coords

        # Build index of previous titles
        prev_idx = {t: i for i, t in enumerate(self._prev_titles)}
        cur_indices, prev_indices = [], []
        for ci, t in enumerate(titles):
            pi = prev_idx.get(t)
            if pi is not None:
                cur_indices.append(ci)
                prev_indices.append(pi)

        if len(cur_indices) < 3:
            log.info("umap: < 3 shared titles, skipping Procrustes alignment")
            self._prev_coords = coords.copy()
            self._prev_titles = list(titles)
            return coords

        cur_pts = coords[cur_indices]
        prev_pts = self._prev_coords[prev_indices]

        # Center both point sets
        cur_mean = cur_pts.mean(axis=0)
        prev_mean = prev_pts.mean(axis=0)
        cur_c = cur_pts - cur_mean
        prev_c = prev_pts - prev_mean

        # Optimal rotation via SVD
        H = cur_c.T @ prev_c
        U, _, Vt = np.linalg.svd(H)
        R = Vt.T @ U.T

        # Apply rotation + translation to ALL points
        aligned = (coords - cur_mean) @ R.T + prev_mean

        self._prev_coords = aligned.copy()
        self._prev_titles = list(titles)
        return aligned

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self, path: str) -> None:
        """Pickle reducer + previous coords to *path*."""
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        joblib.dump(
            {
                "reducer": self._reducer,
                "prev_coords": self._prev_coords,
                "prev_titles": self._prev_titles,
            },
            path,
        )

    def load(self, path: str) -> None:
        """Restore state from *path*.  No-op if the file is missing."""
        if not Path(path).exists():
            return
        try:
            data = joblib.load(path)
            self._reducer = data.get("reducer")
            self._prev_coords = data.get("prev_coords")
            self._prev_titles = data.get("prev_titles")
        except Exception:
            log.warning("umap: failed to load %s, starting fresh", path)
