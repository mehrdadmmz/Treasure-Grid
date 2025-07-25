# Grid Rush


Treasure Grid is a fast-paced, multi-player “mine-sweeper” style game on a 10×10 grid. Up to 5 players connect to a central server; each unrevealed cell is a shared resource protected by a per-cell mutex. Players click cells simultaneously to “claim” them; which reveal an emoji which can affect the player’s score according to the Point System below. 

---

## Point system

🥳 (Player gets 10 points added to their score)
😁 (Player gets 5 points added to their score)
😐 (Player gets no points added to their score)
😡 (Player loses 5 points from their score)
🤬 (Player loses 10 points from their score)

---

## Compile and Run

To run the program, run these commands in order

```bash
python server.py
```

```bash
python client.py 127.0.0.1 Alice
```

```bash
python client.py 127.0.0.1 Bob
```





