# CLAUDE.md

## Project Overview

Portfolio website for Sebastian Frey (Applied ML Engineer / Data Scientist).
Live at **https://itssebastianfrey.com** via GitHub Pages.

## Tech Stack

- **Framework:** Astro 5.12 (static site generation)
- **Styling:** Tailwind CSS 4.1 via `@tailwindcss/vite`
- **Font:** IBM Plex Mono (monospace throughout)
- **Deployment:** GitHub Pages with custom domain

## Commands

```bash
npm run dev      # local dev server (http://localhost:4321)
npm run build    # production build → dist/
npm run preview  # preview built site
```

## Project Structure

- `src/config.ts` — **Single source of truth** for all site content (projects, experience, education, skills, social links). Edit this file to update content — no need to touch components.
- `src/layouts/MainLayout.astro` — Base HTML template (head, fonts, meta)
- `src/components/` — Header, Hero, About, Projects, Experience, Education, Footer
- `src/pages/index.astro` — Homepage (assembles all components)
- `src/pages/projects/` — Dedicated project detail pages:
  - `biasbreaker.astro` — LLM news bias neutralization
  - `latent-discovery.astro` — Clustering comparison (K-Means/GMM/HDBSCAN)
  - `sentinel-ltv.astro` — XGBoost churn prediction
  - `eternal-chess.astro` — Live multiplayer chess via WebSocket
  - `wiki-pulse.astro` — Real-time Wikipedia topic clustering dashboard (UMAP scatter + live WS)
- `src/styles/global.css` — Tailwind imports + base styles
- `public/images/projects/` — Project screenshots and visualizations

## Eternal Chess (Server)

The `server/` directory contains the WebSocket game server deployed on a DigitalOcean VPS (`64.226.115.193`).

- `server/main.py` — FastAPI + WebSocket server (python-chess for validation, httpx for GitHub sync)
- `server/docker-compose.yml` — Docker Compose with Caddy reverse proxy for SSL
- `server/Dockerfile` — Python 3.12 slim image
- `server/Caddyfile` — Routes `chess.itssebastianfrey.com` → backend:8000
- `server/requirements.txt` — fastapi, uvicorn, python-chess, httpx, python-dotenv

### WebSocket Protocol

The frontend (`eternal-chess.astro`) and server communicate via JSON messages:

| Direction | Type | Payload |
|-----------|------|---------|
| Server → Client | `init` | `{type, fen, moves, move_count, turn, result}` |
| Client → Server | move | `{move: "e4"}` |
| Server → All | `move` | `{type, move, fen, turn, move_count}` |
| Server → Sender | `error` | `{type, message, fen}` |
| Server → All | `viewers` | `{type, count}` |
| Server → All | `game_over` | `{type, result, fen, move_count}` |

### Deployment Status

- DNS: `chess.itssebastianfrey.com` → A record → `64.226.115.193` (needs to be set up)
- SSL: Caddy auto-provisions Let's Encrypt certificates
- Frontend WS URL: set via `PUBLIC_WS_URL` in `.env` (build-time injection via `define:vars`)

## Environment Variables (.env — gitignored)

```
GITHUB_TOKEN=...          # GitHub PAT for game state sync (server-side only)
GITHUB_REPO=...           # e.g. Sebastian-Frey/eternal-chess
PUBLIC_WS_URL=...         # WebSocket URL injected into Eternal Chess at build time
PUBLIC_WIKI_WS_URL=...    # WebSocket URL injected into Wiki Pulse at build time
```

## Wiki Pulse (WebSocket Protocol)

The frontend (`wiki-pulse.astro`) connects to the Wiki Pulse backend via WebSocket:

| Direction | Type | When | Payload |
|-----------|------|------|---------|
| Server → Client | `init` | On connect | `{type, period, stats, snapshot: {clusters, members}}` |
| Server → Client | `stats` | Every 30s | `{type, edits_per_min, active_articles, cluster_count, embedded_articles}` |
| Server → Client | `snapshot` | New cluster data | `{type, period, period_start, clusters, members}` |
| Client → Server | `subscribe` | Period change | `{type: "subscribe", period: "day|week|month"}` |

The WS URL is set via `PUBLIC_WIKI_WS_URL` in `.env` (build-time injection via `define:vars`).

## Key Conventions

- **Update CHANGELOG.md** with every change made to the project.
- All site content is centralized in `src/config.ts` — don't hardcode content in components.
- Project detail pages use a consistent nav bar (fixed, glassmorphism on scroll, "Projects" highlighted).
- The server IP must never appear in source code — use `PUBLIC_WS_URL` env var.
- Astro `<script is:inline>` blocks cannot use template expressions with curly braces in HTML — use `&#123;` / `&#125;` HTML entities in `<pre>` code display blocks.
- The Eternal Chess project description in `config.ts` still references the old GitOps approach — update it when going live with WebSocket.

## Design Language

- Accent color: `#1d4ed8` (blue-700)
- Dark sections: `bg-slate-950` with `border-slate-800`
- Typography: monospace throughout, `text-[10px]` to `text-[11px]` for labels, uppercase + tracking-widest
- Project pages: large title with accent span, metrics ribbons, dark code blocks, tech stack pill badges
- Eternal Chess: cyberpunk aesthetic — neon blue accents, glitch CSS on title, grid background pattern
