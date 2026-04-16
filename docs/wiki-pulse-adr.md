# ADR-001: Hybrid storage for Wiki Pulse (DuckDB on VPS + Supabase)

- **Status:** Accepted
- **Date:** 2026-04-14
- **Context project:** Wiki Pulse (portfolio subpage)

## Context

Wiki Pulse ingests the English Wikipedia edit firehose, embeds unique articles with a sentence-transformer, and runs HDBSCAN + UMAP every 60 seconds to produce topic clusters for a public dashboard. Two data shapes coexist:

1. **Hot working set** — article summaries, 384-dim embeddings, hourly edit buckets. Read every 60 seconds by the clusterer. High write volume (hundreds of upserts/min). Estimated 90-day footprint: ~1–2 GB.
2. **Cold read-model** — cluster snapshots and aggregate stats. Read by the browser on every page load. Low write volume (a few rows/minute at most). Estimated 90-day footprint: ~80–150 MB.

Existing infra:
- Supabase free tier (500 MB Postgres, always-on). Already used for other small projects.
- DigitalOcean VPS (`64.226.115.193`) running Eternal Chess under Docker Compose + Caddy. Has spare CPU and disk.

## Decision

Split storage by access pattern:

- **Hot set → DuckDB file on the VPS** (`/var/lib/wikipulse/state.duckdb`), bind-mounted into the `wikipulse` container.
- **Cold read-model → Supabase Postgres**, with Row Level Security granting the `anon` key read-only access so the Astro frontend can read it directly without going through the VPS API.

## Alternatives considered

1. **Everything in Supabase (with pgvector).** Rejected: embeddings alone (~300–750 MB) plus edit buckets (~600 MB–1 GB) would blow the 500 MB free-tier cap on day one. Would force a paid plan purely for infra the VPS can handle for free.
2. **Everything on the VPS (SQLite/DuckDB + local API for cluster reads).** Rejected for the read path: each page load would hit the VPS API, coupling frontend latency to VPS health. Supabase gives us a CDN-backed read-through API for free and keeps the dashboard partially functional even if the VPS is down (frontend still shows the last snapshot).
3. **Postgres on the VPS.** Rejected: adds operational surface (backups, upgrades) for no gain over DuckDB for this workload. DuckDB's columnar layout + array functions are a better fit for embedding-heavy hot queries anyway.

## Consequences

**Positive**
- Free tier stays free.
- Hot-path reads (clusterer → embeddings) are local-file fast — no network round trip.
- Frontend reads the read-model directly from Supabase; the VPS only serves the live WebSocket.
- DuckDB's array + linear algebra functions make cosine-similarity sanity checks trivial.
- Public anon key is safe to ship; service role key stays server-side.

**Negative**
- Two storage systems to reason about. Mitigation: clean separation — hot stuff never leaves the VPS; cold stuff is write-only from the VPS and read-only from the browser.
- DuckDB file lives on the VPS disk; if the droplet is lost, the 90-day working set is lost. Acceptable: it rebuilds itself from the live stream in ~24h. Snapshots survive in Supabase.
- If Wiki Pulse ever needs historical queries beyond 90 days, DuckDB will need either longer retention or a cold-archive path. Not in scope for v1.

## Related

- `docs/wiki-pulse-plan.md` — overall implementation plan.
- Existing Eternal Chess service — pattern for Docker Compose + Caddy reverse proxy + env-driven config.
