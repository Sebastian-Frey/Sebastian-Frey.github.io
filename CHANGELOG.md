# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Changed
- **Wiki Pulse — Period-switch responsiveness & cluster diversity** — Seven related fixes addressing (a) the Day/Week/Month buttons feeling laggy and (b) weekly sometimes producing only 2 clusters:
  1. *Optimistic UI* (`wiki-pulse.astro`): period click now immediately clears the scatter, treemap, heatmap, cluster cards, and legend, and swaps the overlay text to `Loading {period}…`. Active button gets `animate-pulse`. Stale snapshots for a period the user already switched away from are ignored.
  2. *Frontend rate-limit handling* (`wiki-pulse.astro`): new `rate_limited` WebSocket error handler parses `retry_after` and schedules a resubscribe via `setTimeout`. Tracks `pendingPeriod` so the latest-clicked period always wins.
  3. *Lower WS subscribe cooldown* (`ws.py`): `SUBSCRIBE_COOLDOWN` reduced from 5 s to 1 s.
  4. *Explicit rate-limited ack* (`ws.py`): `ConnectionManager.set_period()` now returns `float` (seconds-remaining instead of silent False). Endpoint sends `{type:"error", code:"rate_limited", retry_after, period}` to the client so it can retry instead of staring at stale data.
  5. *Offload blocking I/O* (`ws.py`): `_compute_stats` and `_fetch_snapshot` are now awaited via `loop.run_in_executor` in both the endpoint init path and the 30 s poll loop. No longer blocks the event loop on Supabase/DuckDB round-trips.
  6. *Per-period HDBSCAN tuning* (`config.py` + `clusterer.py`): split the `MIN_CLUSTER_SIZE` gate from HDBSCAN's own `min_cluster_size`. Day uses `min_cluster_size=12, selection="eom"` (stable). Week uses `8, "leaf"` and month uses `10, "leaf"` — more, smaller clusters so thematic groups don't collapse into one megacluster. Override via `WIKIPULSE_HDBSCAN_{DAY,WEEK,MONTH}_{SIZE,SELECT}` env vars.
  7. *Stratified sampling* (`config.py` + `clusterer.py`): the DuckDB query no longer blindly takes top-2000 by edit count. It now takes top 75 % by edit count and random-samples the remaining 25 % from ranks `head+1 … head × 3`. Head preserves popular signal; tail adds diversity so weekly has more to cluster on. Tunable via `WIKIPULSE_STRATIFIED_TAIL_FRACTION` / `_POOL_MULT`.
  8. *Upsert-then-prune* (`clusterer.py`): Supabase writes now insert the fresh `cluster_snapshots` + `cluster_members` rows BEFORE deleting obsolete ones. Eliminates the brief window (observable by the 30 s poll loop) where a snapshot had been deleted but its replacement not yet written. Delete is now scoped via `NOT IN (new_cluster_ids)` / diffed title set rather than wholesale.

### Added
- **Wiki Pulse — Tutorial walkthrough modal** — New `TUTORIAL` button in the top nav of `src/pages/projects/wiki-pulse.astro` opens a 5-step illustrated popup explaining the pipeline with concrete, non-technical examples (Taylor Swift / Beyoncé cluster as music, Black Hole as space, etc.). Slides: (01) The Firehose — ~150 edits/min visualised as flying article pills, (02) Turn words into numbers — three articles mapped to colored 384-dim fingerprint bars where similar topics produce similar patterns, (03) Group the similar ones — HDBSCAN clustering visualised as three emergent blobs with noise points, (04) Squish 384D into a map — stacked dimensions collapsed into a 2D scatter via UMAP, (05) Name each cluster — c-TF-IDF word cloud producing a human-readable label. All illustrations are inline SVG (zero new assets, zero bandwidth). Features: progress bar, prev/next arrows, dot indicators, keyboard nav (ESC/arrows), click-outside-to-close, final-slide CTA that smooth-scrolls to the live UMAP canvas, first-visit auto-open gated by `localStorage['wp_tutorial_seen']`. Reuses the BiasBreaker modal + slideshow pattern.
- **Wiki Pulse (phase 5 — frontend + WebSocket)** — `app/ws.py` replaced with a full ConnectionManager + background poll loop. Clients connect via WebSocket, receive initial snapshot + live stats every 30 s, and can subscribe to day/week/month periods. Rate-limited subscribe messages (5 s cooldown). `src/pages/projects/wiki-pulse.astro` is a modern light-themed dashboard page with: live metrics ribbon (edits/min, active articles, clusters, embedded), interactive UMAP scatter plot on Canvas (hover tooltips, click-to-highlight clusters, animated transitions on new data), cluster cards grid with labels/size/momentum/top terms, four-section ML methodology breakdown (Stream Ingestion, Semantic Embedding, Density-Based Clustering, Procrustes Alignment) targeting DS/ML hiring managers, pipeline flowchart, WebSocket protocol code block, and tech stack pills. No database credentials, server IPs, or API keys exposed in client code. Wiki Pulse added to `config.ts` projects array.
- **Wiki Pulse (phase 4 — clusterer)** — `app/clusterer.py` runs three cadences (daily/60 s, weekly/15 min, monthly/1 h) that query DuckDB for recently-edited articles with embeddings, cluster them with HDBSCAN (`min_cluster_size` from env, `eom` selection), project to 2-D via UMAP (Procrustes-aligned to the previous run for layout stability), and label clusters with class-based c-TF-IDF. Results (snapshots + per-article membership with UMAP coords) are written to Supabase `cluster_snapshots` and `cluster_members`. CPU-bound work (HDBSCAN, UMAP) is offloaded to the thread executor to keep the event loop free. `app/labels.py` implements `ctfidf_labels()` using scikit-learn's `CountVectorizer`. `app/umap_state.py` implements `UmapState` with `fit_initial`/`transform`/`align_to_previous`/`save`/`load` using `joblib` persistence. `/api/stats` now returns a real `cluster_count` from Supabase. `/api/snapshot` and `/api/cluster/{period}/{cluster_id}` serve live cluster data from Supabase with graceful fallback when unavailable.
- **Wiki Pulse (phase 3 — embedder)** — `app/embedder.py` drains `state.needs_embedding` in batches of 200 every 30 s, fetches `rest_v1/page/summary/{title}` at 10-wide concurrency with the Wikimedia UA, embeds `title + extract` using `sentence-transformers/all-MiniLM-L6-v2` (384-dim, normalized, CPU) and upserts into DuckDB `articles`. 24 h in-process LRU guards against re-embedding on every edit. `/api/stats` gains `embedded_articles`. `requirements.txt` re-enables the ML stack (CPU-only torch via PyTorch's wheel index to keep the image lean).
- **Wiki Pulse (phase 2 — ingest + bucketer)** — Real Wikimedia SSE ingest (`app/ingestor.py`) filters to enwiki mainspace non-bot edits and pushes normalised events onto an asyncio queue with exponential backoff on disconnect. `app/bucketer.py` drains the queue every 30 s, aggregates by `(title, hour_bucket)`, and upserts into DuckDB `edit_buckets` with a per-title editor-count approximation. New `app/state.py` holds the shared rolling edits-per-minute counter, `needs_embedding` set, `last_edits` tail, and the single DuckDB connection. `/api/stats` is now live — returns real `edits_per_min`, distinct active articles in the last 24 h, and pending-embedding queue size.
- **Wiki Pulse (scaffold)** — `server/wiki-pulse/` skeleton: FastAPI entrypoint, stub ingestor/bucketer/embedder/clusterer/labels/umap_state modules, DuckDB + Supabase storage helpers, REST + WebSocket route stubs, Supabase `001_init.sql` migration, Dockerfile, requirements. `server/docker-compose.yml` gains a `wikipulse` service with a `wikipulse_data` volume; `server/Caddyfile` gains the `wiki.itssebastianfrey.com` reverse-proxy block. `.env.example` seeded. Follow-up phases (ingestor → embedder → clusterer → API → Astro page) build on this scaffolding.

## 2026-04-05

### Changed
- **Email obfuscation** — email address is now base64-encoded and assembled client-side via JS, preventing automated scraping from static HTML. Added reusable `EmailLink.astro` component used in Hero, Footer, and Eternal Chess pages.

## 2026-03-27

### Added
- **Round-robin queue system** — when 3+ people are online, each person makes one move then goes to the back of the line. Server enforces turn order. Clients get real-time queue position updates.
- **Piece move animations** — pieces slide smoothly from source to destination square (200ms CSS transition with absolute-positioned clone overlay)
- **Sound effects** — move, capture, check, and turn notification sounds (Lichess-sourced, MIT license) in `public/sounds/`
- **Browser notifications** — "It's your turn!" notification when queue rotates to you (with permission prompt)
- **"How to Play" section** — description between hero and metrics explaining the shared game, controls, and queue system
- **Last-move highlighting** — source and destination squares glow blue after each move
- **Check highlighting** — king square glows red when in check
- **Queue bar UI** — green "YOUR TURN" or amber "Position #X" bar above the board, with input disabled when waiting

- **Server offline notice** — red bar above the board with "Server Offline" message and contact email (sc.frey@aol.de) shown when WebSocket connection is down, hidden when reconnected
- **Check banner** — red "CHECK!" bar appears above the board when a king is in check, auto-hides on next move
- **Game over overlay** — prominent amber overlay with result text and "Vote to Restart" button when game ends
- **Vote to restart** — majority-vote restart system. Server tracks votes, broadcasts vote count. Button in game-over overlay and inline below the board during active games. Votes clear on new move or when game restarts.
- **Stronger piece contrast** — white pieces pure white (#ffffff) with glow, black pieces darker slate (#475569) with shadow for clear visual separation
- `CLAUDE.md` — Project instructions file for Claude Code
- `README.md` — Project documentation
- `PROJECTS.md` — Detailed project descriptions

### Changed
- `server/main.py` — ConnectionManager refactored from flat list to `dict[str, WebSocket]` + ordered queue list. Each client assigned a UUID. New `queue` and `restart_vote` message types. Move broadcasts include `from`, `to`, `is_capture`, `is_check` fields for animations/sounds. Vote-to-restart with majority threshold.
- `src/pages/projects/eternal-chess.astro` — Queue UI, animation system, sound preloader, check/game-over banners, vote restart, turn guards, stronger piece colors
- `src/config.ts` — Updated Eternal Chess description from GitOps to WebSocket architecture, updated skill tags

## 2026-03-23

### Changed
- `src/pages/projects/eternal-chess.astro` - Replaced GitHub API polling with live WebSocket connection (`ws://64.226.115.193:8000/ws`)
  - Board now receives initial FEN via `init` message on socket open
  - Moves sent via `socket.send(JSON.stringify({ move: san }))` instead of GitHub `repository_dispatch`
  - Incoming `move` messages update board for all connected viewers in real time
  - Added `SERVER: ONLINE/OFFLINE` status badge in nav with WebSocket connection state
  - Added reconnect with exponential backoff on disconnect
  - Updated metrics ribbon: Total Moves, Latency (ms), Protocol (WebSocket), Connected Viewers
  - Updated dashboard: Server Status replaces Pipeline Status, live connection indicator
  - Updated flowchart: User Move → WS Send → Server Validate → Broadcast → Board Refresh
  - Updated code snippet to show WebSocket message format
  - Updated tech stack tags (WebSocket, FastAPI, Real-Time Multiplayer)
  - Optimistic local move rendering with server-side error rollback

### Added
- `server/main.py` - Production rewrite: ConnectionManager class, GitHub as source of truth (fetch FEN on startup via httpx, non-blocking push after every move via asyncio.create_task), python-dotenv for secrets, full docker-logs print statements
- `.env` - Added GITHUB_TOKEN and GITHUB_REPO keys (gitignored)

### Removed
- `referee.py` - No longer needed (server-side validation now on WebSocket server)
- `game_state.json` - State managed by WebSocket server, not a JSON file
- `.github/workflows/move-referee.yml` - GitHub Action replaced by live server

## 2026-03-22

### Added
- `src/pages/projects/eternal-chess.astro` - New project page: Eternal Chess (serverless multiplayer chess via GitOps)
- `.github/workflows/move-referee.yml` - GitHub Action for move validation via python-chess
- `referee.py` - Python referee script that validates SAN moves and updates game_state.json
- `game_state.json` - Initial chess game state (starting position)
- Eternal Chess entry added to `config.ts` projects array and `PROJECTS.md`

### Design
- Cyberpunk aesthetic: slate-950 background, electric blue neon accents
- Glitch effect on title text
- Live chess board with click-to-move and SAN text input
- GitOps dashboard side panel with telemetry, commit history, and PGN viewer
- CSS-based 5-step workflow flowchart (User Move → API Dispatch → Referee → Commit → Refresh)
- Syntax-highlighted code snippets for referee.py and move-referee.yml
- Metrics ribbon: Total Commits, Avg Latency, Runtime, Infrastructure

## 2026-03-20

### Added
- `README.md` - Project documentation
- `CHANGELOG.md` - Change tracking file
- `PROJECTS.md` - Detailed project descriptions

## [Latest] - 2026-03-20

### Current State
- Astro 5.12 + Tailwind CSS 4.1 portfolio site
- 6 projects showcased (3 with dedicated detail pages)
- Sections: Hero, About, Projects, Experience, Education
- Responsive design with IBM Plex Mono typography
- Interactive elements: modals, carousels, scroll animations
- Deployed to GitHub Pages at itssebastianfrey.com

### Previous Changes (from git history)
- Updated project display and descriptions
- Added clustering comparison detail page
- Added paper link for Master's Thesis (arXiv)
- Added SentinelLTV project page
