"""
Treasure Grid – server
──────────────────────
• Classic / Spooky / Space themes, 3-second preview, spectators.
• One round per launch; no “Play again / RESET” flow anymore.
"""

import json
import random
import socket
import sys
import threading
import time
from board import Board

# ─────────────────── configuration ───────────────────────────────────
HOST       = "0.0.0.0"
PORT       = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
BOARD_SIZE = 10
TIME_LIMIT = 60          # seconds after BEGIN

AVATARS = ["😎", "🤖", "🐱", "🐶", "🦄", "👾", "🦊", "🐼",
           "🐸", "🐵", "🐯", "🐨", "🥸", "🦁", "🐙"]
THEMES  = ["Classic", "Spooky", "Space"]
PREVIEW_SECONDS = 3

# =====================================================================
class TreasureServer:
    def __init__(self):
        self._init_state()
        self.lock = threading.Lock()             # protects players dict

    def _init_state(self):
        self.next_id      = 1
        self.players      = {}                   # pid → {...}
        self.board        = Board(BOARD_SIZE)
        self.theme        = "Classic"
        self.game_started = False
        self.start_time   = None
        self.tick_handle  = None

    # ────────────────── helpers: networking ──────────────────────────
    def _broadcast(self, msg: dict):
        data = (json.dumps(msg) + "\n").encode()
        for p in list(self.players.values()):
            try: p["sock"].sendall(data)
            except OSError: pass

    def _send_player_list(self):
        payload = [
            {"player": pid, "name": p["name"], "avatar": p["avatar"],
             "ready": p["ready"], "spectate": p["spectator"]}
            for pid, p in self.players.items()
        ]
        self._broadcast({"type": "PLAYERS", "players": payload,
                         "theme": self.theme})

    # ────────────────── game flow control ────────────────────────────
    def _maybe_start_game(self):
        if self.game_started: return
        if not self.players:  return
        if not all(p["ready"] for p in self.players.values()
                   if not p["spectator"]):
            return

        # preview phase
        self.game_started = True
        self.board        = Board(BOARD_SIZE)      # fresh board

        layout = [[sq.coins for sq in row] for row in self.board.grid]
        self._broadcast({"type": "START", "size": BOARD_SIZE,
                         "theme": self.theme, "layout": layout,
                         "preview": PREVIEW_SECONDS})
        threading.Timer(PREVIEW_SECONDS, self._begin_round).start()

    def _begin_round(self):
        self.start_time = time.time()
        self._broadcast({"type": "BEGIN"})
        self._tick_timer()

    def _tick_timer(self):
        remaining = TIME_LIMIT - int(time.time() - self.start_time)
        self._broadcast({"type": "TIME", "left": max(0, remaining)})

        if remaining <= 0 or self.board.all_revealed():
            self._finish_game()
        else:
            self.tick_handle = threading.Timer(1, self._tick_timer)
            self.tick_handle.start()

    def _finish_game(self):
        if self.tick_handle:
            self.tick_handle.cancel()
            self.tick_handle = None

        board = sorted(((pid, p["score"]) for pid, p in self.players.items()),
                       key=lambda x: -x[1])
        leaderboard = [{"player": pid, "name": self.players[pid]["name"],
                        "score": sc} for pid, sc in board]
        top = leaderboard[0]["score"] if leaderboard else 0
        winners = [d["player"] for d in leaderboard if d["score"] == top]

        self._broadcast({"type": "GAMEOVER",
                         "leaderboard": leaderboard,
                         "winners": winners})

    def _check_auto_win(self):
        if self.game_started and len([p for p in self.players.values()
                                      if not p["spectator"]]) < 2:
            self._finish_game()

    # ────────────────── per-client thread ────────────────────────────
    def _client_thread(self, conn: socket.socket):
        file, pid = conn.makefile("r"), None
        try:
            with self.lock:
                pid = self.next_id; self.next_id += 1
                spectator = bool(self.game_started)
                self.players[pid] = {
                    "sock": conn, "file": file,
                    "name": f"P{pid}", "avatar": random.choice(AVATARS),
                    "ready": False if not spectator else True,
                    "spectator": spectator,
                    "score": 0, "streak": 0,
                }

            conn.sendall((json.dumps(
                {"type": "WELCOME", "player": pid,
                 "avatar": self.players[pid]["avatar"],
                 "spectator": spectator, "size": BOARD_SIZE}) + "\n").encode())
            self._send_player_list()

            for line in file:
                try: msg = json.loads(line.strip())
                except json.JSONDecodeError: continue
                self._handle_msg(pid, msg)
        finally:
            with self.lock:
                if pid in self.players: self.players.pop(pid)
                self._send_player_list(); self._check_auto_win()
            print(f"[SERVER] Player {pid} disconnected")

    # ────────────────── message handler ──────────────────────────────
    def _handle_msg(self, pid: int, msg: dict):
        p = self.players.get(pid);  typ = msg.get("type")
        if not p: return

        if typ == "NAME" and not self.game_started:
            p["name"] = msg.get("name", f"P{pid}")
            self._send_player_list()

        elif typ == "THEME" and not self.game_started:
            requested = msg.get("theme", "Classic")
            if requested in THEMES:
                self.theme = requested; self._send_player_list()

        elif typ == "READY" and not self.game_started and not p["spectator"]:
            p["ready"] = True; self._send_player_list(); self._maybe_start_game()

        elif typ == "CHAT":
            text = msg.get("msg", "").strip()
            if text:
                self._broadcast({"type": "CHAT", "player": pid,
                                 "name": p["name"], "avatar": p["avatar"],
                                 "msg": text})

        elif typ == "CLICK" and self.game_started and not p["spectator"]:
            r, c = msg["row"], msg["col"]
            if self.board.lock_square(r, c, pid):
                self._broadcast({"type": "LOCK", "row": r, "col": c,
                                 "player": pid})
                threading.Timer(0.3, self._reveal_square,
                                args=(pid, r, c)).start()

    # ────────────────── reveal helper ────────────────────────────────
    def _reveal_square(self, pid, r, c):
        val   = self.board.reveal_square(r, c, pid)
        p     = self.players[pid]

        if val == -1:
            p["streak"] += 1
            coins = -5 if p["streak"] == 3 else -1
            if coins == -5: p["streak"] = 0
        else:
            p["streak"] = 0; coins = val

        p["score"] += coins
        self._broadcast({"type": "REVEAL", "row": r, "col": c,
                         "player": pid, "coins": coins})
        self._broadcast({"type": "SCORE", "player": pid,
                         "score": p["score"]})

        if self.board.all_revealed(): self._finish_game()

    # ────────────────── main loop ────────────────────────────────────
    def serve_forever(self):
        with socket.create_server((HOST, PORT), reuse_port=True) as s:
            print(f"[SERVER] Listening on {PORT} …")
            while True:
                conn, _ = s.accept()
                threading.Thread(target=self._client_thread,
                                 args=(conn,), daemon=True).start()


# =====================================================================
if __name__ == "__main__":
    TreasureServer().serve_forever()