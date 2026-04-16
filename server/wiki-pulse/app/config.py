"""Environment-driven configuration for the Wiki Pulse service."""
from __future__ import annotations

import os

SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

DATA_DIR = os.environ.get("WIKIPULSE_DATA_DIR", "/var/lib/wikipulse")
DUCKDB_PATH = f"{DATA_DIR}/state.duckdb"

USER_AGENT = os.environ.get(
    "WIKIPULSE_USER_AGENT", "WikiPulse/0.1 (sc.frey@aol.de)"
)
MIN_CLUSTER_SIZE = int(os.environ.get("WIKIPULSE_MIN_CLUSTER_SIZE", "15"))
MAX_CLUSTER_ARTICLES = int(os.environ.get("WIKIPULSE_MAX_CLUSTER_ARTICLES", "2000"))

WIKI_SSE_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
