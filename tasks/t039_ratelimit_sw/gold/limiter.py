"""スライディングウィンドウ・レート制限 (複数キー独立, O(1)償却)."""

from __future__ import annotations

from collections import defaultdict, deque


class SlidingWindowRateLimiter:
    def __init__(self, limit: int, window: float) -> None:
        if limit <= 0 or window <= 0:
            raise ValueError("limit and window must be positive")
        self.limit = limit
        self.window = window
        self._events: dict = defaultdict(deque)

    def allow(self, key, now: float) -> bool:
        q = self._events[key]
        threshold = now - self.window
        # ウィンドウ外 (now-window 以前) のイベントを捨てる。
        while q and q[0] <= threshold:
            q.popleft()
        if len(q) < self.limit:
            q.append(now)
            return True
        return False
