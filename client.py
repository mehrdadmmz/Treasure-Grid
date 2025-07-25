# client.py
import json
import os
import queue
import socket
import sys
import threading
import tkinter as tk
from tkinter import messagebox

# ── optional sound support ───────────────────────────────────────────
try:
    from playsound import playsound          # pip install playsound==1.3.0
except ImportError:
    playsound = None                         # game still works without sound
# ─────────────────────────────────────────────────────────────────────

# ---------------- command-line defaults ------------------------------
HOST         = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
NAME_DEFAULT = sys.argv[2] if len(sys.argv) > 2 else "Player"
PORT         = int(sys.argv[3]) if len(sys.argv) > 3 else 6000

# ---------------- colour + sound mapping -----------------------------
COLOR_CHOICES = [
    ("Green",  "#2ecc71"),
    ("Red",    "#e74c3c"),
    ("Blue",   "#3498db"),
    ("Yellow", "#f1c40f"),
]

EMOJI = {0: "💣", 1: "🥉", 2: "🥈", 3: "🥇"}

# Build absolute paths for the .wav files that sit next to this script
_here = os.path.abspath(os.path.dirname(__file__))
SOUND_FILE = {
    0: os.path.join(_here, "bomb.wav"),    # 💣
    1: os.path.join(_here, "bronze.wav"),  # 🥉
    2: os.path.join(_here, "silver.wav"),  # 🥈
    3: os.path.join(_here, "gold.wav"),    # 🥇
}

# =====================================================================
class ClientGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("550x600")
        self.configure(bg="#222")
        self.title("Treasure Grid – Lobby")

        # local state
        self.q           = queue.Queue()
        self.players     = {}          # pid ➜ {name,color,ready}
        self.pid         = None
        self.my_name     = NAME_DEFAULT
        self.my_color    = None
        self.color_btns  = {}          # hex ➜ btn widget

        # header vars
        self.time_var  = tk.StringVar(value="⏳ …")
        self.score_var = tk.StringVar(value="⭐ 0")

        self._build_header()
        self._build_lobby()
        self.current_view = "lobby"

        # networking thread
        threading.Thread(target=self._net_thread, daemon=True).start()
        self.after(50, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._close)

    # ────────────────── UI builders ──────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg="#222")
        hdr.pack(fill="x")
        tk.Label(hdr, textvariable=self.time_var,
                 fg="white", bg="#222").pack(side="left", padx=10)
        tk.Label(hdr, textvariable=self.score_var,
                 fg="white", bg="#222").pack(side="right", padx=10)
        self.players_lbl = tk.Label(hdr, fg="white", bg="#222")
        self.players_lbl.pack(pady=4)

    def _build_lobby(self):
        self.lobby = tk.Frame(self, bg="#222")
        self.lobby.pack(expand=True)

        tk.Label(self.lobby, text="Treasure Grid",
                 fg="white", bg="#222", font=("Helvetica", 18, "bold")).pack(pady=6)
        tk.Label(self.lobby, text="Pick a colour, enter name, press Ready",
                 fg="white", bg="#222").pack(pady=2)

        # name entry
        nrow = tk.Frame(self.lobby, bg="#222")
        nrow.pack(pady=4)
        tk.Label(nrow, text="Name:", fg="white", bg="#222").pack(side="left")
        self.name_ent = tk.Entry(nrow, width=12)
        self.name_ent.insert(0, self.my_name)
        self.name_ent.pack(side="left")
        tk.Button(nrow, text="Set", command=self._set_name).pack(side="left", padx=5)

        # colour selection
        crow = tk.Frame(self.lobby, bg="#222")
        crow.pack(pady=8)
        for _, hexcol in COLOR_CHOICES:
            btn = tk.Button(
                crow,
                bg=hexcol,
                activebackground=hexcol,
                width=6,
                height=3,
                relief="raised",
                bd=2,
                command=lambda c=hexcol: self._pick_color(c),
            )
            btn.pack(side="left", padx=7)
            self.color_btns[hexcol] = btn

        self.ready_btn = tk.Button(self.lobby, text="Ready",
                                   state="disabled", command=self._ready)
        self.ready_btn.pack(pady=10)

    def _build_grid(self, size: int):
        self.grid = tk.Frame(self, bg="#222")
        self.grid.pack(expand=True)
        self.btns = [[None]*size for _ in range(size)]
        for r in range(size):
            for c in range(size):
                b = tk.Button(
                    self.grid,
                    width=3,
                    height=2,
                    bg="#ddd",
                    relief="flat",
                    command=lambda r=r, c=c: self._click(r, c),
                )
                b.grid(row=r, column=c, padx=1, pady=1)
                self.btns[r][c] = b

    # ────────────────── lobby actions ────────────────────────────────
    def _pick_color(self, hexcol):
        self.my_color = hexcol
        self._send({"type": "COLOR", "color": hexcol})
        # visually mark chosen colour
        for btn in self.color_btns.values():
            btn.config(relief="raised")
        self.color_btns[hexcol].config(relief="sunken")
        self._maybe_enable_ready()

    def _set_name(self):
        n = self.name_ent.get().strip()
        if n:
            self.my_name = n
            self._send({"type": "NAME", "name": n})
            self._maybe_enable_ready()

    def _maybe_enable_ready(self):
        if self.my_color and self.my_name:
            self.ready_btn.config(state="normal")

    def _ready(self):
        self.ready_btn.config(state="disabled")
        self._send({"type": "READY"})

    # ────────────────── gameplay actions ─────────────────────────────
    def _click(self, r, c):
        self._send({"type": "CLICK", "row": r, "col": c})

    # ────────────────── networking ───────────────────────────────────
    def _net_thread(self):
        try:
            self.sock = socket.create_connection((HOST, PORT))
        except OSError as e:
            self.q.put({"type": "ERROR", "msg": str(e)})
            return

        self._send({"type": "JOIN", "name": self.my_name})
        for line in self.sock.makefile("r"):
            try:
                self.q.put(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass

    def _send(self, msg: dict):
        try:
            self.sock.sendall((json.dumps(msg) + "\n").encode())
        except Exception:
            pass

    # ────────────────── queue pump & handler ─────────────────────────
    def _pump(self):
        try:
            while True:
                self._handle(self.q.get_nowait())
        except queue.Empty:
            pass
        self.after(50, self._pump)

    def _handle(self, m: dict):
        t = m.get("type")

        if t == "WELCOME":
            self.pid = m["player"]

        elif t == "PLAYERS":
            self.players = {d["player"]: d for d in m["players"]}
            self._update_players()
            self._update_colour_buttons()

        elif t == "START":
            if self.current_view == "lobby":
                self.lobby.destroy()
                self._build_grid(m.get("size", 10))
                self.current_view = "game"
                self.title("Treasure Grid")

        elif t == "TIME":
            self.time_var.set(f"⏳ {m['left']}s")

        elif t == "LOCK":
            r, c, owner = m["row"], m["col"], m["player"]
            color = self.players.get(owner, {}).get("color", "#888")
            self.btns[r][c].config(bg=color, state="disabled")

        elif t == "REVEAL":
            r, c, coins, owner = m["row"], m["col"], m["coins"], m["player"]
            color = self.players.get(owner, {}).get("color", "#666")
            self.btns[r][c].config(text=EMOJI.get(coins, "?"), bg=color)
            if owner == self.pid and playsound and coins in SOUND_FILE:
                threading.Thread(
                    target=playsound,
                    args=(SOUND_FILE[coins],),
                    daemon=True,
                ).start()

        elif t == "SCORE" and m["player"] == self.pid:
            self.score_var.set(f"⭐ {m['score']}")

        elif t == "GAMEOVER":
            self._leaderboard(m["leaderboard"], m["winners"])

        elif t == "ERROR":
            messagebox.showerror("Connection Error", m["msg"])
            self._close()

    # ────────────────── helper views ────────────────────────────────
    def _update_players(self):
        txt = ", ".join(
            f"{d['name']}{' ✔' if d['ready'] else ''}" for d in self.players.values()
        )
        self.players_lbl.config(text="Players: " + txt)

    def _update_colour_buttons(self):
        taken = {d["color"] for d in self.players.values() if d["color"]}
        for hexcol, btn in self.color_btns.items():
            if hexcol in taken and hexcol != self.my_color:
                btn.config(state="disabled")
            else:
                btn.config(state="normal")

    def _leaderboard(self, lb, winners):
        lines = [f"{d['name']} – {d['score']} ⭐" for d in lb]
        messagebox.showinfo("🏆 Leaderboard 🏆", "\n".join(lines))
        messagebox.showinfo(
            "Result", "You win!" if self.pid in winners else "Game over!"
        )
        self._close()

    # ────────────────── cleanup ──────────────────────────────────────
    def _close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.destroy()


# =====================================================================
if __name__ == "__main__":
    ClientGUI().mainloop()
