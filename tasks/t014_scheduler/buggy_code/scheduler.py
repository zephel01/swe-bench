"""Job scheduling on top of the priority queue."""

from pq import PriorityQueue


class Scheduler:
    """Collects jobs and yields them in priority order."""

    def __init__(self):
        self._queue = PriorityQueue()

    def add_job(self, name, priority=0):
        """Register a job with a numeric priority (higher runs first)."""
        self._queue.push(name, priority)

    def run_order(self):
        """Drain the queue and return job names in execution order."""
        order = []
        while len(self._queue) > 0:
            order.append(self._queue.pop())
        return order
