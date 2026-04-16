"""Process-global runtime state shared between the ingestor, bucketer,
embedder, clusterer, and the API handlers.

The whole service runs in one asyncio event loop, so ordinary attribute
access is safe — no locks needed.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any, Deque


class AppState:
    def __init__(self) -> None:
        self._edit_times: Deque[float] = deque()
        self.needs_embedding: set[str] = set()
        self.last_edits: Deque[dict[str, Any]] = deque(maxlen=50)
        self.db: Any = None  # duckdb connection, set during startup

    def record_edit(self, ts: float) -> None:
        self._edit_times.append(ts)
        self._trim()

    def _trim(self) -> None:
        cutoff = time.time() - 60.0
        while self._edit_times and self._edit_times[0] < cutoff:
            self._edit_times.popleft()

    def edits_per_min(self) -> int:
        self._trim()
        return len(self._edit_times)


state = AppState()
