"""Priority queue: higher priority number = served first."""

import heapq


class PriorityQueue:
    """Max-priority queue with FIFO order for equal priorities."""

    def __init__(self):
        self._heap = []
        self._count = 0

    def push(self, item, priority):
        """Add item with the given numeric priority."""
        heapq.heappush(self._heap, (-priority, self._count, item))
        self._count += 1

    def pop(self):
        """Remove and return the item with the highest priority."""
        if not self._heap:
            raise IndexError("pop from empty queue")
        return heapq.heappop(self._heap)[2]

    def __len__(self):
        return len(self._heap)
