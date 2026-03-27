"""
Eternal Chess — Production WebSocket Game Server

Run:   python main.py
Deps:  pip install fastapi uvicorn python-chess httpx python-dotenv
Env:   GITHUB_TOKEN, GITHUB_REPO (loaded from .env)
"""

import asyncio
import json
import uuid
from base64 import b64decode, b64encode
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from os import environ

import chess
import httpx
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

GITHUB_TOKEN: str = environ["GITHUB_TOKEN"]
GITHUB_REPO: str = environ["GITHUB_REPO"]
GITHUB_API = "https://api.github.com"
STATE_PATH = "game_state.json"

QUEUE_THRESHOLD = 3  # queue activates when this many viewers are connected


# ═══════════════════════════════════════════════════════════════════
#  Connection Manager (with round-robin queue)
# ═══════════════════════════════════════════════════════════════════

class ConnectionManager:
    def __init__(self) -> None:
        self.connections: dict[str, WebSocket] = {}  # client_id -> ws
        self.queue: list[str] = []                   # ordered turn queue

    async def connect(self, ws: WebSocket) -> str:
        await ws.accept()
        client_id = uuid.uuid4().hex[:8]
        self.connections[client_id] = ws
        self.queue.append(client_id)
        print(f"[CONNECT] {client_id} joined — {len(self.connections)} viewer(s)")
        return client_id

    def disconnect(self, client_id: str) -> None:
        was_first = len(self.queue) > 0 and self.queue[0] == client_id
        self.connections.pop(client_id, None)
        if client_id in self.queue:
            self.queue.remove(client_id)
        print(f"[DISCONNECT] {client_id} left — {len(self.connections)} viewer(s)")
        if was_first and self.queue:
            print(f"[QUEUE] Turn holder left — next up: {self.queue[0]}")

    def viewer_count(self) -> int:
        return len(self.connections)

    def queue_enabled(self) -> bool:
        return self.viewer_count() >= QUEUE_THRESHOLD

    def is_turn(self, client_id: str) -> bool:
        if not self.queue_enabled():
            return True  # free play when < threshold
        return len(self.queue) > 0 and self.queue[0] == client_id

    def rotate_queue(self, client_id: str) -> None:
        if client_id in self.queue:
            self.queue.remove(client_id)
            self.queue.append(client_id)

    def queue_position(self, client_id: str) -> int:
        try:
            return self.queue.index(client_id)
        except ValueError:
            return -1

    async def send_personal(self, client_id: str, message: dict) -> None:
        ws = self.connections.get(client_id)
        if not ws:
            return
        try:
            await ws.send_json(message)
        except Exception:
            self.disconnect(client_id)

    async def broadcast(self, message: dict) -> None:
        dead: list[str] = []
        for cid, ws in self.connections.items():
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(cid)
        for cid in dead:
            self.disconnect(cid)

    async def broadcast_viewers(self) -> None:
        await self.broadcast({"type": "viewers", "count": self.viewer_count()})

    async def broadcast_queue_state(self) -> None:
        enabled = self.queue_enabled()
        for cid in list(self.connections.keys()):
            pos = self.queue_position(cid)
            await self.send_personal(cid, {
                "type": "queue",
                "enabled": enabled,
                "position": pos,
                "total": len(self.queue),
                "is_your_turn": pos == 0 if enabled else True,
            })


manager = ConnectionManager()


# ═══════════════════════════════════════════════════════════════════
#  Game State
# ═══════════════════════════════════════════════════════════════════

board = chess.Board()
move_history: list[str] = []
move_count: int = 0
restart_votes: set[str] = set()  # client IDs that voted to restart


def get_result() -> str:
    if board.is_checkmate():
        return "0-1" if board.turn == chess.WHITE else "1-0"
    if board.is_stalemate():
        return "Draw (Stalemate)"
    if board.is_insufficient_material():
        return "Draw (Insufficient Material)"
    if board.is_fifty_moves():
        return "Draw (50-Move Rule)"
    if board.is_repetition():
        return "Draw (Repetition)"
    return "*"


def build_state_json() -> str:
    return json.dumps({
        "fen": board.fen(),
        "moves": move_history,
        "move_count": move_count,
        "result": get_result(),
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }, indent=2)


# ═══════════════════════════════════════════════════════════════════
#  GitHub Sync
# ═══════════════════════════════════════════════════════════════════

def _gh_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


async def fetch_state_from_github() -> dict | None:
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{STATE_PATH}"
    async with httpx.AsyncClient() as client:
        resp = await client.get(url, headers=_gh_headers())

    if resp.status_code == 404:
        print("[GITHUB] game_state.json not found in repo — starting fresh")
        return None
    if resp.status_code != 200:
        print(f"[GITHUB] Failed to fetch state: {resp.status_code} {resp.text[:200]}")
        return None

    data = resp.json()
    content = b64decode(data["content"]).decode()
    state = json.loads(content)
    print(f"[GITHUB] Fetched state: {state.get('move_count', 0)} moves")
    return state


async def push_state_to_github() -> None:
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/contents/{STATE_PATH}"
    headers = _gh_headers()

    async with httpx.AsyncClient() as client:
        sha: str | None = None
        get_resp = await client.get(url, headers=headers)
        if get_resp.status_code == 200:
            sha = get_resp.json().get("sha")
        elif get_resp.status_code != 404:
            print(f"[GITHUB] SHA fetch failed: {get_resp.status_code}")
            return

        content_b64 = b64encode(build_state_json().encode()).decode()
        body: dict = {
            "message": f"♟ Move #{move_count}: {move_history[-1] if move_history else 'init'}",
            "content": content_b64,
            "committer": {
                "name": "eternal-chess-bot",
                "email": "chess@eternal.bot",
            },
        }
        if sha:
            body["sha"] = sha

        put_resp = await client.put(url, headers=headers, json=body)
        if put_resp.status_code in (200, 201):
            print(f"[GITHUB] Synced move #{move_count} to repo")
        else:
            print(f"[GITHUB] Sync FAILED: {put_resp.status_code} {put_resp.text[:200]}")


def schedule_github_sync() -> None:
    asyncio.create_task(_safe_github_sync())


async def _safe_github_sync() -> None:
    try:
        await push_state_to_github()
    except Exception as e:
        print(f"[GITHUB] Sync error (non-fatal): {e}")


# ═══════════════════════════════════════════════════════════════════
#  Lifespan (replaces deprecated on_event)
# ═══════════════════════════════════════════════════════════════════

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: fetch state from GitHub. Shutdown: clean up."""
    global board, move_history, move_count

    print("[STARTUP] Fetching game state from GitHub...")
    state = await fetch_state_from_github()

    if state:
        try:
            board = chess.Board(state["fen"])
            move_history = state.get("moves", [])
            move_count = state.get("move_count", 0)
            print(f"[STARTUP] Resumed game — {move_count} moves, turn: {'White' if board.turn else 'Black'}")
        except Exception as e:
            print(f"[STARTUP] Corrupt state, starting fresh: {e}")
            board = chess.Board()
            move_history = []
            move_count = 0
    else:
        board = chess.Board()
        move_history = []
        move_count = 0
        print("[STARTUP] Fresh game initialized")

    print(f"[STARTUP] Server ready — FEN: {board.fen()}")

    yield  # ── server runs here ──

    print("[SHUTDOWN] Server stopping")


# ═══════════════════════════════════════════════════════════════════
#  FastAPI App
# ═══════════════════════════════════════════════════════════════════

app = FastAPI(title="Eternal Chess", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ═══════════════════════════════════════════════════════════════════
#  WebSocket Endpoint
# ═══════════════════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    global board, move_history, move_count

    client_id = await manager.connect(websocket)

    try:
        await manager.send_personal(client_id, {
            "type": "init",
            "fen": board.fen(),
            "moves": move_history,
            "move_count": move_count,
            "turn": "w" if board.turn == chess.WHITE else "b",
            "result": get_result(),
            "your_id": client_id,
        })
        await manager.broadcast_viewers()
        await manager.broadcast_queue_state()
    except Exception:
        manager.disconnect(client_id)
        return

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await manager.send_personal(client_id, {
                    "type": "error",
                    "message": "Invalid JSON",
                    "fen": board.fen(),
                })
                continue

            # ── Vote to restart ──
            if data.get("action") == "vote_restart":
                restart_votes.add(client_id)
                needed = max(2, (manager.viewer_count() + 1) // 2)  # majority
                print(f"[VOTE] {client_id} voted to restart ({len(restart_votes)}/{needed})")
                await manager.broadcast({
                    "type": "restart_vote",
                    "votes": len(restart_votes),
                    "needed": needed,
                })
                if len(restart_votes) >= needed:
                    board.reset()
                    move_history.clear()
                    move_count = 0
                    restart_votes.clear()
                    print("[RESET] Game restarted by vote")
                    await manager.broadcast({
                        "type": "init",
                        "fen": board.fen(),
                        "moves": [],
                        "move_count": 0,
                        "turn": "w",
                        "result": "*",
                    })
                    await manager.broadcast_queue_state()
                    schedule_github_sync()
                continue

            # ── Move handling ──
            move_san = data.get("move")
            if not move_san:
                await manager.send_personal(client_id, {
                    "type": "error",
                    "message": "No move provided",
                    "fen": board.fen(),
                })
                continue

            # Queue enforcement
            if not manager.is_turn(client_id):
                pos = manager.queue_position(client_id)
                await manager.send_personal(client_id, {
                    "type": "error",
                    "message": f"Wait your turn! You are #{pos + 1} of {len(manager.queue)} in the queue.",
                    "fen": board.fen(),
                })
                continue

            if board.is_game_over():
                await manager.send_personal(client_id, {
                    "type": "error",
                    "message": f"Game is over: {get_result()}",
                    "fen": board.fen(),
                })
                continue

            try:
                move = board.parse_san(move_san)
            except (chess.InvalidMoveError, chess.IllegalMoveError, chess.AmbiguousMoveError):
                print(f"[MOVE] ILLEGAL: '{move_san}' from {client_id}")
                await manager.send_personal(client_id, {
                    "type": "error",
                    "message": f"Illegal move: {move_san}",
                    "fen": board.fen(),
                })
                continue

            # Capture info before pushing
            is_capture = board.is_capture(move)
            from_sq = chess.square_name(move.from_square)
            to_sq = chess.square_name(move.to_square)

            board.push(move)
            move_history.append(move_san)
            move_count += 1
            restart_votes.clear()  # clear restart votes on new move

            is_check = board.is_check()
            turn = "w" if board.turn == chess.WHITE else "b"
            result = get_result()

            print(f"[MOVE] #{move_count}: {move_san} by {client_id}  FEN: {board.fen()}")

            await manager.broadcast({
                "type": "move",
                "move": move_san,
                "fen": board.fen(),
                "turn": turn,
                "move_count": move_count,
                "from": from_sq,
                "to": to_sq,
                "is_capture": is_capture,
                "is_check": is_check,
            })

            if board.is_game_over():
                print(f"[GAME OVER] {result}")
                await manager.broadcast({
                    "type": "game_over",
                    "result": result,
                    "fen": board.fen(),
                    "move_count": move_count,
                })

            # Rotate queue after successful move
            manager.rotate_queue(client_id)
            await manager.broadcast_queue_state()

            schedule_github_sync()

    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"[ERROR] WebSocket loop: {e}")
    finally:
        manager.disconnect(client_id)
        restart_votes.discard(client_id)
        await manager.broadcast_viewers()
        await manager.broadcast_queue_state()


# ═══════════════════════════════════════════════════════════════════
#  HTTP Endpoints
# ═══════════════════════════════════════════════════════════════════

@app.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "fen": board.fen(),
        "move_count": move_count,
        "viewers": manager.viewer_count(),
        "queue": manager.queue,
        "game_over": board.is_game_over(),
        "result": get_result(),
    }


RESET_SECRET: str = environ.get("RESET_SECRET", "")


@app.post("/reset")
async def reset_game(secret: str = "") -> dict:
    if not RESET_SECRET or secret != RESET_SECRET:
        return {"error": "unauthorized"}
    global board, move_history, move_count
    board = chess.Board()
    move_history = []
    move_count = 0
    print("[RESET] Game reset to starting position")

    await manager.broadcast({
        "type": "init",
        "fen": board.fen(),
        "moves": [],
        "move_count": 0,
        "turn": "w",
        "result": "*",
    })

    await manager.broadcast_queue_state()
    schedule_github_sync()
    return {"status": "reset", "fen": board.fen()}


# ═══════════════════════════════════════════════════════════════════
#  Entry Point — so `python main.py` works in Docker
# ═══════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
