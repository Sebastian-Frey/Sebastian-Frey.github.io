"""DuckDB + Supabase client helpers.

Hot working set lives in a local DuckDB file on the VPS; cluster snapshots
and ingest stats are written to Supabase (see ``docs/wiki-pulse-adr.md``).
"""
from __future__ import annotations

import logging
import os
from typing import Optional

import duckdb

from . import config

log = logging.getLogger(__name__)


def get_duckdb() -> duckdb.DuckDBPyConnection:
    os.makedirs(config.DATA_DIR, exist_ok=True)
    return duckdb.connect(config.DUCKDB_PATH)


def init_schema(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        create table if not exists articles (
          title       varchar primary key,
          summary     varchar,
          embedding   float[384],
          first_seen  timestamp,
          last_edited timestamp
        );
        """
    )
    conn.execute(
        """
        create table if not exists edit_buckets (
          title        varchar,
          hour_bucket  timestamp,
          edit_count   integer,
          byte_delta   integer,
          editor_count integer,
          primary key (title, hour_bucket)
        );
        """
    )
    conn.execute(
        "create index if not exists edit_buckets_hour on edit_buckets(hour_bucket);"
    )
    log.info("storage: duckdb schema ready at %s", config.DUCKDB_PATH)


def get_supabase():
    """Return a Supabase service-role client, or ``None`` if unconfigured."""
    if not config.SUPABASE_URL or not config.SUPABASE_SERVICE_KEY:
        log.warning("storage: supabase credentials missing; writes will be skipped")
        return None
    # Lazy import so the service can boot without supabase-py installed
    # during scaffolding-only deploys.
    from supabase import create_client  # type: ignore

    return create_client(config.SUPABASE_URL, config.SUPABASE_SERVICE_KEY)
