"""Sliding window rate limiting."""


class SlidingWindowRateLimiter:
    """Allow at most max_requests per window_sec seconds."""

    def __init__(self, max_requests, window_sec):
        if max_requests <= 0 or window_sec <= 0:
            raise ValueError("max_requests and window_sec must be positive")
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._hits = []

    def allow(self, now):
        """Record a request at time `now`; return True if it is allowed."""
        cutoff = now - self.window_sec
        self._hits = [t for t in self._hits if t > cutoff]
        if len(self._hits) <= self.max_requests:
            self._hits.append(now)
            return True
        return False

    def pending(self, now):
        """Return how many requests are currently inside the window."""
        cutoff = now - self.window_sec
        return sum(1 for t in self._hits if t > cutoff)
