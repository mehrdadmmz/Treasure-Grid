# board.py
import random
import threading


class SquareState:
    """Internal enum for a cell’s state."""
    HIDDEN   = "hidden"
    LOCKED   = "locked"
    REVEALED = "revealed"


class Square:
    """A single cell on the board."""
    def __init__(self):
        # 40 % chance to hide 1–3 coins; 60 % bomb (0 coins)
        self.coins = random.choice([0] * 6 + [1, 2, 3, 1])
        self.state = SquareState.HIDDEN
        self.owner = None  # player ID who locked / revealed


class Board:
    """Thread-safe board with lock/reveal operations."""
    def __init__(self, size: int = 10):
        self.size     = size
        self.grid     = [[Square() for _ in range(size)] for _ in range(size)]
        self._lock    = threading.Lock()
        self.revealed = 0
        self.total    = size * size

    # ── concurrency helpers ──────────────────────────────────────────
    def lock_square(self, row: int, col: int, player_id: int) -> bool:
        """Try to lock a hidden square for player_id. Return True if lock succeeds."""
        with self._lock:
            sq = self.grid[row][col]
            if sq.state != SquareState.HIDDEN:
                return False
            sq.state, sq.owner = SquareState.LOCKED, player_id
            return True

    def reveal_square(self, row: int, col: int, player_id: int) -> int:
        """
        Reveal a square previously locked by player_id.
        Returns the number of coins (0 if empty or if player_id mismatched).
        """
        with self._lock:
            sq = self.grid[row][col]
            if sq.state != SquareState.LOCKED or sq.owner != player_id:
                return 0
            sq.state = SquareState.REVEALED
            self.revealed += 1
            return sq.coins

    def all_revealed(self) -> bool:
        """Check if every square on the board has been revealed."""
        return self.revealed >= self.total
