# 🗺️ Treasure Grid

**Treasure Grid** is a multiplayer Mines-style game built with Python. Players race to uncover a grid filled with bombs and treasure, aiming to score the highest points in 60 seconds.

## 🎮 Features

- Real-time multiplayer gameplay using sockets
- Graphical user interface (GUI) with `tkinter`
- Multiple emoji themes: Classic, Spooky, Space
- Spectator mode with live updates
- Bomb streak penalty system
- Thread-safe game board logic

## 🧩 Game Rules

- Click tiles to reveal coins or bombs.
- Coins:
  - 🥉 = +1 point
  - 🥈 = +2 points
  - 🥇 = +3 points
- Bombs:
  - 💣 = -1 point
  - 3 bombs in a row = 💀 = -5 points
- Highest score after 60 seconds wins!

## 🚀 Getting Started

### Requirements

- Python 3.7+
- `tkinter` (usually bundled with Python)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/mehrdadmmz/Socket-371.git
   cd treasure-grid
   ```

2. Install dependencies (none required beyond standard library):
   ```bash
   pip install -r requirements.txt
   ```

### Running the Game

#### 1. Start the server:
```bash
python server.py [port]
```
_Default port is `6000` if not specified._

#### 2. Start clients (in separate terminals or machines):
```bash
python client.py [host] [player_name] [port]
```
- `host`: IP address of the server (default: `127.0.0.1`)
- `player_name`: Optional name to show in-game
- `port`: Optional port (default: `6000`)

## 🧠 Project Structure

```
board.py    # Game board and square logic (thread-safe)
server.py   # Game server logic using sockets and threading
client.py   # GUI client built with tkinter
```

## 🛠️ Notes

- Ensure all clients use the same port as the server.
- Works on LAN or localhost.
- Tested on Python 3.10.

## 📜 License

MIT License. See `LICENSE` file for details.
