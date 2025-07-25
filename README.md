# Grid Rush


Treasure Grid is a fast-paced, multi-player “mine-sweeper” style game on a 10×10 grid. Up to 5 players connect to a central server; each unrevealed cell is a shared resource protected by a per-cell mutex. Players click cells simultaneously to “claim” them; which reveal an emoji which can affect the player’s score according to the Point System below. 

---

## Point system

- 🥇 (Player gets 3 points added to their score)
- 🥈 (Player gets 2 points added to their score)
- 🥉 (Player gets 1 points added to their score)
- 💣 (Player gets 0 points added to their score)


---

## Compile and Run

To run the server, run this command on one computer

```bash
python server.py
```

To play this game on a computer, run these commands

```bash
python client.py <ip address of compter running the server> <your name> <port>
```

For example if the server ip is 127.0.0.1, your name is Bob, and the port number you want to use is 6000 you would type...

```bash
python client.py 207.23.192.227 Bob 6000
```





