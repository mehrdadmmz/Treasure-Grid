"""
Treasure Grid – server
──────────────────────
• Lobby: players pick a colour + name, press Ready
• Game starts when every connected player has both a colour and ready=True
• If, during a game, fewer than two players remain connected,
  the last player standing wins immediately.
• 60-second timer once game begins; leaderboard sent at end
• Messages exchanged one-per-line in JSON
"""

import json
import socket
import sys
import threading
import time
from board import Board

# ─────────────────── configuration ───────────────────────────────────
HOST         = "127.0.0.1"
PORT         = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
BOARD_SIZE   = 10
TIME_LIMIT   = 60                # seconds per round

# =====================================================================
class TreasureServer:
    def __init__(self):
        self.board       = Board(BOARD_SIZE)
        self.players     = {}    # pid ➜ dict(sock,file,name,color,ready,score)
        self.next_id     = 1

        self.game_started = False
        self.start_time   = None
        self.tick_handle  = None

        self.lock = threading.Lock()        # protects players dict + ids

    # ────────────────── helpers: network ──────────────────────────────
    def _broadcast(self, msg: dict):
        data = (json.dumps(msg) + "\n").encode()
        for p in list(self.players.values()):
            try:
                p["sock"].sendall(data)
            except OSError:
                pass                        # ignore broken clients

    def _send_player_list(self):
        payload = [
            {
                "player": pid,
                "name":   p["name"],
                "color":  p["color"],
                "ready":  p["ready"],
            }
            for pid, p in self.players.items()
        ]
        self._broadcast({"type": "PLAYERS", "players": payload})

    # ────────────────── helpers: game flow ────────────────────────────
    def _maybe_start_game(self):
        if self.game_started:
            return
        if self.players and all(p["ready"] and p["color"]
                                for p in self.players.values()):
            self.game_started = True
            self.start_time   = time.time()
            self.board        = Board(BOARD_SIZE)    # new board each round
            self._broadcast({"type": "START", "size": BOARD_SIZE})
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

        # compile leaderboard
        board = sorted(
            ((pid, p["score"]) for pid, p in self.players.items()),
            key=lambda kv: -kv[1]
        )
        leaderboard = [
            {
                "player": pid,
                "name":   self.players[pid]["name"],
                "score":  sc,
                "color":  self.players[pid]["color"],
            }
            for pid, sc in board
        ]
        top_score = leaderboard[0]["score"] if leaderboard else 0
        winners   = [d["player"] for d in leaderboard if d["score"] == top_score]

        self._broadcast({"type": "GAMEOVER",
                         "leaderboard": leaderboard,
                         "winners": winners})
        self.game_started = False

    # ────────────────── auto-win helper ───────────────────────────────
    def _check_auto_win(self):
        """
        Called after any player disconnect. If a game is active and fewer than
        two players remain, the remaining player wins immediately.
        """
        if self.game_started and len(self.players) < 2:
            self._finish_game()

    # ────────────────── per-client thread ─────────────────────────────
    def _client_thread(self, conn: socket.socket):
        file = conn.makefile("r")
        pid  = None
        try:
            with self.lock:
                pid = self.next_id
                self.next_id += 1
                self.players[pid] = {
                    "sock":  conn,
                    "file":  file,
                    "name":  f"P{pid}",
                    "color": None,
                    "ready": False,
                    "score": 0,
                }

            # handshake
            conn.sendall((json.dumps({"type": "WELCOME",
                                      "player": pid,
                                      "size": BOARD_SIZE}) + "\n").encode())
            self._send_player_list()

            for line in file:
                try:
                    msg = json.loads(line.strip())
                except json.JSONDecodeError:
                    continue
                self._handle_msg(pid, msg)

        finally:
            # disconnect cleanup
            with self.lock:
                if pid in self.players:
                    self.players.pop(pid)
                self._send_player_list()
                self._check_auto_win()
            print(f"[SERVER] Player {pid} disconnected")

    # ────────────────── message dispatcher ───────────────────────────
    def _handle_msg(self, pid: int, msg: dict):
        p = self.players.get(pid)
        if not p:
            return

        typ = msg.get("type")

        if typ == "JOIN":       # initial join already handled
            pass

        elif typ == "NAME":
            p["name"] = msg.get("name", f"P{pid}")
            self._send_player_list()

        elif typ == "COLOR":
            requested = msg.get("color")
            # allow only one player per colour
            if requested and all(pl["color"] != requested
                                 for pl in self.players.values()):
                p["color"] = requested
                self._send_player_list()
                self._maybe_start_game()

        elif typ == "READY":
            p["ready"] = True
            self._send_player_list()
            self._maybe_start_game()

        elif typ == "CLICK" and self.game_started:
            r, c = msg["row"], msg["col"]
            if self.board.lock_square(r, c, pid):
                self._broadcast({"type": "LOCK",
                                 "row": r, "col": c,
                                 "player": pid})
                threading.Timer(0.3,
                                self._reveal_square,
                                args=(pid, r, c)).start()

    # ────────────────── reveal helper ────────────────────────────────
    def _reveal_square(self, pid: int, r: int, c: int):
        coins = self.board.reveal_square(r, c, pid)
        self.players[pid]["score"] += coins

        self._broadcast({"type": "REVEAL",
                         "row": r, "col": c,
                         "player": pid,
                         "coins": coins})
        self._broadcast({"type": "SCORE",
                         "player": pid,
                         "score": self.players[pid]["score"]})

        if self.board.all_revealed():
            self._finish_game()

    # ────────────────── main loop ────────────────────────────────────
    def serve_forever(self):
        with socket.create_server((HOST, PORT)) as s:
            print(f"[SERVER] Listening on {PORT} …")
            while True:
                conn, _ = s.accept()
                threading.Thread(target=self._client_thread,
                                 args=(conn,), daemon=True).start()


# =====================================================================
if __name__ == "__main__":
    TreasureServer().serve_forever()
