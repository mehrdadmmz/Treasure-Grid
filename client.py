# client.py
import json, queue, random, socket, sys, threading, tkinter as tk
from tkinter import messagebox

# ---------------- command-line defaults ------------------------------
HOST  = sys.argv[1] if len(sys.argv) > 1 else "127.0.0.1"
NAME  = sys.argv[2] if len(sys.argv) > 2 else "Player"
PORT  = int(sys.argv[3]) if len(sys.argv) > 3 else 6000

# ---------------- emoji sets ----------------------------------------
COMMON_NEG = { -5: "💀", -1: "💣" }    # same for every theme

EMOJI_THEME = {
    "Classic": { **COMMON_NEG, 1: "🥉", 2: "🥈", 3: "🥇" },
    "Spooky":  { **COMMON_NEG, 1: "🍂", 2: "🦇", 3: "🎃" },
    "Space":   { **COMMON_NEG, 1: "🛰️", 2: "🪐", 3: "🚀" },
}
THEMES = list(EMOJI_THEME.keys())

# ---------------- reaction texts (theme-agnostic) --------------------
REACTIONS = {
    -5: [r"\Triple boom! \–5 😱", r"\Epic misfire… \–5!", r"\The crowd gasps! −5"],
    -1: [r"\Boom! 💥", r"\Another bomb!", r"\KABOOM!"],
     1: [r"\Bronze—nice!", r"\You’re on the board!", r"\A humble start."],
     2: [r"\Silver! ⚔️", r"\Shiny & smooth.", r"\Climbing up."],
     3: [r"\Gold! 🏆", r"\Jackpot!", r"\Treasure secured!"],
}

class ClientGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.geometry("700x700")
        self.configure(bg="#222")
        self.title("Treasure Grid – Lobby")

        # local state
        self.q           = queue.Queue()
        self.players     = {}
        self.pid         = None
        self.avatar      = "🙂"
        self.spectator   = False
        self.theme       = "Classic"
        self.in_preview  = False

        # header vars
        self.time_var    = tk.StringVar(value="⏳ …")
        self.score_var   = tk.StringVar(value="⭐ 0")
        self.message_var = tk.StringVar(value="")

        self._build_header()
        self._build_lobby()
        self.current_view = "lobby"

        threading.Thread(target=self._net_thread, daemon=True).start()
        self.after(50, self._pump)
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build_header(self):
        hdr = tk.Frame(self, bg="#222")
        hdr.pack(fill="x")
        tk.Label(hdr, textvariable=self.time_var,
                 fg="white", bg="#222").pack(side="left", padx=10)
        tk.Label(hdr, textvariable=self.score_var,
                 fg="white", bg="#222").pack(side="right", padx=10)
        self.players_lbl = tk.Label(hdr, fg="white", bg="#222")
        self.players_lbl.pack(pady=4)
        tk.Label(self, textvariable=self.message_var,
                 fg="#ffdd57", bg="#222",
                 font=("Helvetica", 12, "italic")).pack(pady=5)

    def _build_lobby(self):
        self.lobby = tk.Frame(self, bg="#222")
        self.lobby.pack(expand=True, fill="both", padx=10)

        # left column
        left = tk.Frame(self.lobby, bg="#222")
        left.pack(side="left", fill="y", padx=(0, 10))
        tk.Label(left, text="Treasure Grid", fg="white", bg="#222",
                 font=("Helvetica", 24, "bold")).pack(pady=(12, 6))

        # name row
        nrow = tk.Frame(left, bg="#222")
        nrow.pack(pady=4)
        tk.Label(nrow, text="Name:", fg="white", bg="#222").pack(side="left")
        self.name_ent = tk.Entry(nrow, width=16)
        self.name_ent.insert(0, NAME)
        self.name_ent.pack(side="left")
        tk.Button(nrow, text="Set", command=self._set_name).pack(side="left", padx=5)

        # theme selector
        trow = tk.Frame(left, bg="#222")
        trow.pack(pady=6)
        tk.Label(trow, text="Theme:", fg="white", bg="#222").pack(side="left")
        self.theme_var = tk.StringVar(value=self.theme)
        opt = tk.OptionMenu(trow, self.theme_var, *THEMES,
                      command=lambda _=None: self._change_theme())
        opt.config(width=10)
        opt.pack(side="left")

        # ready button
        self.ready_btn = tk.Button(left, text="Ready", width=12,
                                   command=self._ready, bg="#3a3", fg="white")
        self.ready_btn.pack(pady=10)

        # rules label (store ref for live update)
        self.rules_lbl = tk.Label(left, fg="#ffdd57", bg="#222", justify="left")
        self.rules_lbl.pack(pady=(6, 0))
        self._update_rules()

        # right column → chat
        right = tk.Frame(self.lobby, bg="#111")
        right.pack(side="left", fill="both", expand=True)
        tk.Label(right, text="Lobby chat", fg="#4cf", bg="#111",
                 font=("Helvetica", 14, "bold")).pack(pady=(8, 2))

        self.chat_text = tk.Text(right, height=22, state="disabled",
                                 bg="#000", fg="#ddd", wrap="word")
        self.chat_text.pack(fill="both", expand=True, padx=6)
        crow = tk.Frame(right, bg="#111")
        crow.pack(fill="x", pady=4, padx=6)
        self.chat_entry = tk.Entry(crow)
        self.chat_entry.pack(side="left", fill="x", expand=True)
        self.chat_entry.bind("<Return>", lambda e: self._send_chat())
        tk.Button(crow, text="Send", width=8,
                  command=self._send_chat).pack(side="left", padx=4)

    def _build_grid(self, size: int):
        self.grid = tk.Frame(self, bg="#222")
        self.grid.pack(expand=True)
        self.btns = [[None]*size for _ in range(size)]
        for r in range(size):
            for c in range(size):
                b = tk.Button(self.grid, width=3, height=2, bg="#666", fg="white",
                              relief="flat", font=("Helvetica", 12, "bold"),
                              command=lambda r=r, c=c: self._click(r, c))
                b.grid(row=r, column=c, padx=1, pady=1)
                self.btns[r][c] = b

    def _update_rules(self):
        em = EMOJI_THEME[self.theme]
        txt = (
            "How to play:\n"
            "\n• Click tiles fast\n"
            f"\n• {em[-1]} = −1  ({em[-5]} on 3rd!)\n"
            f"\n• {em[1]} = +1   {em[2]} = +2   {em[3]} = +3\n"
            "\n• Highest score after 60 s wins"
        )
        self.rules_lbl.config(text=txt)

    def _set_name(self):
        n = self.name_ent.get().strip()
        if n:
            self._send({"type": "NAME", "name": n})
            if not self.spectator:
                self.ready_btn.config(state="normal")

    def _change_theme(self):
        chosen = self.theme_var.get()
        if chosen != self.theme:
            self.theme = chosen
            self._update_rules()
            self._send({"type": "THEME", "theme": chosen})

    def _ready(self):
        self.ready_btn.config(state="disabled")
        self._send({"type": "READY"})

    def _send_chat(self):
        txt = self.chat_entry.get().strip()
        if txt:
            self._send({"type": "CHAT", "msg": txt})
            self.chat_entry.delete(0, "end")

    def _click(self, r, c):
        if not self.spectator and not self.in_preview:
            self._send({"type": "CLICK", "row": r, "col": c})

    def _net_thread(self):
        try:
            self.sock = socket.create_connection((HOST, PORT))
        except OSError as e:
            self.q.put({"type": "ERROR", "msg": str(e)})
            return
        self._send({"type": "JOIN", "name": NAME})
        for line in self.sock.makefile("r"):
            try:
                self.q.put(json.loads(line.strip()))
            except json.JSONDecodeError:
                pass

    def _send(self, msg):
        try:
            self.sock.sendall((json.dumps(msg) + "\n").encode())
        except Exception:
            pass

    def _pump(self):
        try:
            while True:
                self._handle(self.q.get_nowait())
        except queue.Empty:
            pass
        self.after(50, self._pump)

    def _handle(self, m):
        t = m.get("type")

        if t == "WELCOME":
            self.pid       = m["player"]
            self.avatar    = m.get("avatar", "🙂")
            self.spectator = m.get("spectator", False)
            if self.spectator:
                self.ready_btn.config(state="disabled")
                self.name_ent.config(state="disabled")

        elif t == "PLAYERS":
            self.players = {d["player"]: d for d in m["players"]}
            if "theme" in m and m["theme"] != self.theme:
                self.theme = m["theme"]
                self.theme_var.set(self.theme)
                self._update_rules()
            self._update_players()

        elif t == "CHAT":
            self._add_chat(f"{m.get('avatar', '💬')} {m.get('name')}: {m.get('msg')}")

        elif t == "START":
            self.in_preview = True
            size, layout = m["size"], m["layout"]
            self.theme = m.get("theme", self.theme)
            self.theme_var.set(self.theme)
            self._update_rules()
            if self.current_view == "lobby":
                self.lobby.destroy()
                self._build_grid(size)
                self.current_view = "game"
            mapping = EMOJI_THEME[self.theme]
            for r in range(size):
                for c in range(size):
                    self.btns[r][c].config(text=mapping[layout[r][c]], bg="#333")

        elif t == "BEGIN":
            mapping = EMOJI_THEME[self.theme]
            for row in self.btns:
                for b in row:
                    b.config(text="", bg="#666")
            self.in_preview = False
            self._countdown(3)

        elif t == "TIME":
            self.time_var.set(f"⏳ {m['left']}s")

        elif t == "LOCK" and not self.in_preview:
            r, c = m["row"], m["col"]
            self.btns[r][c].config(bg="#444", state="disabled")

        elif t == "REVEAL":
            r, c, coins, owner = m["row"], m["col"], m["coins"], m["player"]
            emoji = EMOJI_THEME[self.theme].get(coins, "?")
            self.btns[r][c].config(text=emoji, bg="#222")
            if owner == self.pid:
                self.message_var.set(random.choice(REACTIONS.get(coins, ["..."])))

        elif t == "SCORE" and m["player"] == self.pid:
            self.score_var.set(f"⭐ {m['score']}")

        elif t == "GAMEOVER":
            self._show_gameover(m["leaderboard"], m["winners"])

        elif t == "ERROR":
            messagebox.showerror("Connection Error", m["msg"])
            self._close()

    def _add_chat(self, txt):
        self.chat_text.config(state="normal")
        self.chat_text.insert("end", txt + "\n")
        self.chat_text.see("end")
        self.chat_text.config(state="disabled")

    def _update_players(self):
        lbl = ", ".join(f"{d['avatar']} {d['name']}{' ✔' if d['ready'] else ''}" +
                        (" (\\👀)" if d.get('spectate') else "")
                        for d in self.players.values())
        self.players_lbl.config(text="Players: " + lbl)

    def _countdown(self, n):
        if not hasattr(self, "_ov"):
            self._ov = tk.Label(self, fg="#ffdd57", bg="#222",
                                font=("Helvetica", 60, "bold"))
            self._ov.place(relx=0.5, rely=0.5, anchor="center")
        self._ov.config(text=str(n) if n else "GO!")
        if n:
            self.after(1000, lambda: self._countdown(n-1))
        else:
            self.after(700, self._ov.destroy)

    def _show_gameover(self, lb, winners):
        res = "Tie!" if len(winners) > 1 else f"{self.players[winners[0]]['name']} wins! 🏆"
        lines = "\n".join(f"{d['name']} – {d['score']} ⭐" for d in lb)
        messagebox.showinfo("Leaderboard", lines)
        messagebox.showinfo("Result", res)
        self._close()

    def _close(self):
        try:
            self.sock.close()
        except Exception:
            pass
        self.destroy()

# Main entry point
if __name__ == "__main__":
    ClientGUI().mainloop()