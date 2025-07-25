# Grid Rush

**Grid Rush** is a fast-paced, multiplayer “Minesweeper-style” game played on a 10×10 grid. Up to 5 players can connect to a central server. Each unrevealed cell acts as a shared resource protected by a per-cell mutex. Players simultaneously attempt to claim cells, which then reveal emojis affecting their score according to the point system below.

---

## 🎯 Point System

| Emoji | Description                  | Points |
|-------|------------------------------|--------|
| 🥇    | Gold Medal                   | +3     |
| 🥈    | Silver Medal                 | +2     |
| 🥉    | Bronze Medal                 | +1     |
| 💣    | Bomb                         | +0     |

---

## 🖥️ How to Run

### 1. Install Requirements

Make sure you have Python 3 installed. Then install dependencies with:

```bash
pip install -r requirements.txt
```

### 2. Start the Server

On one machine (the host/server):

```bash
python server.py
```

### 3. Start a Client

On each player’s machine:

```bash
python client.py <server_ip> <port>
```

**Example:**

```bash
python client.py 127.0.0.1 6000
```

---

## 🧑‍💻 Notes

- Ensure all players are on the same network or that the server is publicly accessible.
- Each player must use a unique name and port number.
