# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

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
