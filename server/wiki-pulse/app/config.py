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

# Gate: skip the entire cluster run if fewer than this many articles are available.
MIN_CLUSTER_SIZE = int(os.environ.get("WIKIPULSE_MIN_CLUSTER_SIZE", "15"))
MAX_CLUSTER_ARTICLES = int(os.environ.get("WIKIPULSE_MAX_CLUSTER_ARTICLES", "2000"))

# HDBSCAN tuning per period. Lower `min_cluster_size` produces more, smaller
# clusters; "leaf" selection emits every persistent sub-cluster (richer topic
# map at the cost of stability), while "eom" picks the most persistent ones
# (conservative, fewer clusters). Daily stays on EOM/12 for stability; weekly
# and monthly use leaf with a lower threshold so small thematic groups don't
# collapse into one megacluster.
HDBSCAN_PARAMS: dict[str, dict] = {
    "day":   {"min_cluster_size": int(os.environ.get("WIKIPULSE_HDBSCAN_DAY_SIZE",   "12")),
              "selection": os.environ.get("WIKIPULSE_HDBSCAN_DAY_SELECT",   "eom")},
    "week":  {"min_cluster_size": int(os.environ.get("WIKIPULSE_HDBSCAN_WEEK_SIZE",  "8")),
              "selection": os.environ.get("WIKIPULSE_HDBSCAN_WEEK_SELECT",  "leaf")},
    "month": {"min_cluster_size": int(os.environ.get("WIKIPULSE_HDBSCAN_MONTH_SIZE", "10")),
              "selection": os.environ.get("WIKIPULSE_HDBSCAN_MONTH_SELECT", "leaf")},
}

# Stratified sampling: instead of the top-N by edit count, mix the head with
# a random draw from the mid-tail so diverse thematic clusters survive. Set
# STRATIFIED_TAIL_FRACTION to 0 to revert to pure top-N.
STRATIFIED_TAIL_FRACTION = float(os.environ.get("WIKIPULSE_STRATIFIED_TAIL_FRACTION", "0.25"))
STRATIFIED_TAIL_POOL_MULT = float(os.environ.get("WIKIPULSE_STRATIFIED_TAIL_POOL_MULT", "3.0"))

WIKI_SSE_URL = "https://stream.wikimedia.org/v2/stream/recentchange"
WIKI_SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
