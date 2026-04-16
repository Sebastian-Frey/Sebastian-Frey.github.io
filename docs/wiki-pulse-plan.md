# Wiki Pulse — Implementation Plan

Live topic-cluster visualization of English Wikipedia edits. New project page for the portfolio, served at `/projects/wiki-pulse`. Live data via `wiki.itssebastianfrey.com` (WebSocket + REST) on the existing DigitalOcean VPS (`64.226.115.193`), alongside Eternal Chess.

## Goal

Answer the question *"what did the world think was worth updating on Wikipedia today / this week / this month?"* with a live, clustered, visual NLP projection. Portfolio-wise it showcases: streaming ingest, embeddings, unsupervised clustering (callback to Latent Discovery), real-time web UX (callback to Eternal Chess), honest probabilistic/aggregated framing.

## Scope decisions (locked)

- **Language:** English Wikipedia only (`wiki == enwiki`, `namespace == 0`, `bot == false`).
- **Refresh:** 60-second snapshot cadence for the daily view. Weekly = every 15 min, Monthly = every hour.
- **Retention:** 90-day rolling window. Evict untouched articles nightly.
- **Labeling:** c-TF-IDF on titles + edit comments per cluster. Cheap, no LLM dependency. Can add an LLM polish pass later.
- **UMAP stability:** Procrustes-aligned day-over-day. Full refit weekly with drift check.
- **Storage:** Hybrid — DuckDB on VPS for hot data (articles + embeddings + hourly edit buckets); Supabase free tier for cluster snapshots + ingest stats (small, durable, frontend can read directly via anon key).

## Estimated footprint (90-day steady state)

| Store | What | Size |
|---|---|---|
| VPS DuckDB | `articles` (title, summary, 384-dim embedding, timestamps) | ~300–750 MB |
| VPS DuckDB | `edit_buckets` (hourly rollup) | ~600 MB–1 GB |
| Supabase | `cluster_snapshots` + `cluster_members` + `ingest_stats` | ~80–150 MB |

Supabase stays well under the 500 MB free tier cap.

## Architecture

```
Wikimedia SSE ─► ingestor ─► in-mem queue ─► bucketer ─► DuckDB.edit_buckets
                                           │
                                           ▼
                                   needs_embedding set
                                           │
                    REST /page/summary ◄───┤ embedder (MiniLM) ─► DuckDB.articles
                                           │
                                           ▼
                       clusterer (60s/15m/1h) ─► Supabase.cluster_snapshots
                                           │                    + cluster_members
                                           ▼
                                    FastAPI API + WS
                                           │
                                           ▼
        Astro page (reads Supabase directly + upgrades to WS for live edits)
```

## Services (single FastAPI app, asyncio tasks)

Deployed as one Docker container `wikipulse` sharing the existing `server/` compose stack.

1. **Ingestor** — `httpx-sse` client on `https://stream.wikimedia.org/v2/stream/recentchange`. Filters → asyncio queue. Auto-reconnect with backoff on drop.
2. **Bucketer** — drains queue every 30s, upserts hourly rollups into `edit_buckets`. Marks new titles in `needs_embedding`.
3. **Embedder** — every 30s pulls up to 200 pending titles, fetches `/api/rest_v1/page/summary/{title}` at 10-wide concurrency (respects Wikimedia rate limit + UA requirement), embeds with `sentence-transformers/all-MiniLM-L6-v2` on CPU. Upserts into `articles`. LRU cache on title to avoid re-embedding within 24h.
4. **Clusterer** — asyncio timers:
   - Daily (60s): pull articles edited in last 24h → HDBSCAN (`min_cluster_size=15`, `min_samples=5`) → UMAP transform against yesterday's saved model → Procrustes-align to yesterday's coords. c-TF-IDF over cluster titles + comments → top 5 terms → cluster label. Momentum = today size / 7d trailing avg for fuzzy-matched label.
   - Weekly (15m), Monthly (1h): same recipe, wider window, their own saved UMAP models.
5. **Eviction** — nightly `DELETE FROM articles WHERE last_edited < now() - 90 days`; cascade to `edit_buckets`.
6. **API**
   - `GET /api/snapshot?period=day|week|month` → frontend fallback (Supabase is the primary read path)
   - `GET /api/stats` → rolling edits/min, active articles, cluster count
   - `GET /api/cluster/{period}/{id}` → full member list + sample edit comments
   - `WS /ws` → live `edit`, `cluster_update`, `stats` messages

## WebSocket protocol

| Direction | Type | Payload |
|---|---|---|
| S→C | `init` | `{stats, last_edits[]}` |
| S→C | `edit` | `{title, cluster_id?, x?, y?, ts}` |
| S→C | `cluster_update` | `{period, period_start, clusters[], generated_at}` |
| S→C | `stats` | `{edits_per_min, active_articles, cluster_count}` |

## Supabase schema (migration `001_init.sql`)

```sql
create table cluster_snapshots (
  period text not null check (period in ('day','week','month')),
  period_start date not null,
  cluster_id int not null,
  label text not null,
  size int not null,
  rep_titles text[] not null,
  top_terms text[] not null,
  momentum float,
  centroid_x float,
  centroid_y float,
  generated_at timestamptz not null default now(),
  primary key (period, period_start, cluster_id)
);

create table cluster_members (
  period text not null,
  period_start date not null,
  title text not null,
  cluster_id int not null,
  umap_x float not null,
  umap_y float not null,
  edit_count int not null,
  primary key (period, period_start, title)
);

create index on cluster_members (period, period_start, cluster_id);

create table ingest_stats (
  ts timestamptz primary key,
  edits_per_min int not null,
  active_articles int not null,
  cluster_count int not null
);

-- RLS: public read-only for the anon key
alter table cluster_snapshots enable row level security;
alter table cluster_members   enable row level security;
alter table ingest_stats      enable row level security;

create policy "anon read" on cluster_snapshots for select to anon using (true);
create policy "anon read" on cluster_members   for select to anon using (true);
create policy "anon read" on ingest_stats      for select to anon using (true);
```

Service role key (used only by the VPS service) writes; anon key (shipped to the browser) reads.

## DuckDB schema (VPS-local, `state.duckdb`)

```sql
create table if not exists articles (
  title       varchar primary key,
  summary     varchar,
  embedding   float[384],
  first_seen  timestamp,
  last_edited timestamp
);

create table if not exists edit_buckets (
  title        varchar,
  hour_bucket  timestamp,
  edit_count   integer,
  byte_delta   integer,
  editor_count integer,
  primary key (title, hour_bucket)
);
create index if not exists edit_buckets_hour on edit_buckets(hour_bucket);
```

## File layout (to add in the repo)

```
server/
  wiki-pulse/
    Dockerfile
    requirements.txt
    migrations/
      001_init.sql                 # paste into Supabase SQL editor
    app/
      main.py                      # FastAPI + asyncio task wiring
      ingestor.py
      bucketer.py
      embedder.py
      clusterer.py
      api.py
      ws.py
      storage.py                   # DuckDB + Supabase clients
      config.py                    # env + constants
      labels.py                    # c-TF-IDF helper
      umap_state.py                # Procrustes-aligned UMAP cache
    README.md
  docker-compose.yml               # + wikipulse service
  Caddyfile                        # + wiki.itssebastianfrey.com block

src/
  pages/projects/wiki-pulse.astro  # the page
  config.ts                        # + Wiki Pulse project card

.env.example                       # + new vars
CHANGELOG.md                       # + entry
docs/
  wiki-pulse-plan.md               # this file
  wiki-pulse-adr.md                # hybrid storage decision
```

## Environment variables

**VPS (`server/.env` or compose env_file):**
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY` (server-side only)
- `WIKIPULSE_DATA_DIR=/var/lib/wikipulse`
- `WIKIPULSE_USER_AGENT=WikiPulse/0.1 (sc.frey@aol.de)` — Wikimedia requires a contact in the UA
- `WIKIPULSE_MIN_CLUSTER_SIZE=15`

**Frontend (`.env`, GitHub Pages build secrets):**
- `PUBLIC_WIKI_WS_URL=wss://wiki.itssebastianfrey.com/ws`
- `PUBLIC_SUPABASE_URL`
- `PUBLIC_SUPABASE_ANON_KEY`

## Caddyfile addition

```
wiki.itssebastianfrey.com {
  reverse_proxy wikipulse:8000
}
```

## Frontend page spec

`src/pages/projects/wiki-pulse.astro`, matching the existing project-page shell:
- Fixed nav bar (glassmorphism on scroll, "Projects" highlighted).
- Hero with large title + accent span, one-line metric ribbon (edits/min, articles tracked, clusters detected, last refresh).
- **Left 70%** canvas: 2D scatter of cluster members, translucent hulls in `#1d4ed8` with labels at centroids, points pulse on live `edit` WS messages.
- **Right 30%**: period toggle (`Today / 7d / 30d`), top-10 clusters list (label, size, momentum arrow, 3 rep article links).
- **Bottom strip**: horizontally scrolling ticker of last 20 edits with cluster pill.
- Cluster click → modal with full member list + sample edit comments.
- Caveats footer: "enwiki mainspace only · bots filtered · edit volume ≠ importance".

## Build phases

1. **Scaffold** — migration SQL + `server/wiki-pulse/` skeleton with empty service modules, `Dockerfile`, `requirements.txt`, compose + Caddyfile updates, `.env.example`, CHANGELOG.
2. **Ingestor + Bucketer** — wire SSE → DuckDB, smoke-test with an edits/min counter printed to logs.
3. **Embedder** — MiniLM on CPU, fill `articles`. Sanity-check with pgvector-style KNN in DuckDB array_cosine_similarity.
4. **Clusterer (daily only)** — HDBSCAN + UMAP + c-TF-IDF → Supabase. Inspect clusters via SQL before touching UI.
5. **API + WS** — FastAPI routes, Caddy route, SSL via Let's Encrypt (auto).
6. **Astro page** — static shell → Supabase data fetch → WS live animation.
7. **Weekly/monthly snapshots** + eviction cron.
8. **Polish** — drill-down modal, caveats, homepage project card, CHANGELOG, README.

## Checklist — what user does

- [ ] DNS A record `wiki` → `64.226.115.193`, DNS-only (gray cloud).
- [ ] Supabase: run `001_init.sql` in SQL editor. Copy project URL + anon key + service key.
- [ ] VPS: add env vars to the compose env file, create `/var/lib/wikipulse` bind-mount dir.
- [ ] Frontend: add `PUBLIC_*` vars to local `.env` and GitHub Pages build secrets.
- [ ] `git pull && docker compose up -d --build wikipulse` on VPS.
- [ ] `dig wiki.itssebastianfrey.com` returns `64.226.115.193`, then hit `https://wiki.itssebastianfrey.com/api/stats` to verify.

## Honest caveats to surface on the page

- enwiki ≠ the world.
- Edit volume ≠ importance (breaking news is over-represented).
- Bot filtering is heuristic and imperfect.
- c-TF-IDF labels are literal; sometimes a cluster label reads oddly — that's a known trade-off vs LLM polish.
