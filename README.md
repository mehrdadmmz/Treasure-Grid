# Grid Rush


Treasure Grid is a fast-paced, multi-player “mine-sweeper” style game on a 10×10 grid. Up to 5 players connect to a central server; each unrevealed cell is a shared resource protected by a per-cell mutex. Players click cells simultaneously to “claim” them; which reveal an emoji which can affect the player’s score according to the Point System below. 

---

## Point system

- 🥳 (Player gets 10 points added to their score)
- 😁 (Player gets 5 points added to their score)
- 😐 (Player gets no points added to their score)
- 😡 (Player loses 5 points from their score)
- 🤬 (Player loses 10 points from their score)

---

## Compile and Run

To run the server, run this command on one computer

```bash
python server.py
```

To play this game on a computer, run these commands

```bash
python client.py <server ip address> <your name>
```

For example if the server ip is 127.0.0.1 and your name is Bob you would type...

```bash
python client.py 127.0.0.1 Bob
```





