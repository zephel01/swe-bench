"""A fixed-capacity resource pool used by saga steps.

Releasing more of a token than is currently held is an error: it signals that a
compensation ran twice, or that bookkeeping drifted out of sync.
"""


class ResourceError(Exception):
    pass


class Pool:
    def __init__(self, capacity):
        self.capacity = capacity
        self.available = capacity
        self._held = {}

    def acquire(self, token, amount):
        if amount <= 0:
            raise ResourceError("amount must be positive")
        if amount > self.available:
            raise ResourceError(f"pool exhausted acquiring {amount} for {token}")
        self._held[token] = self._held.get(token, 0) + amount
        self.available -= amount

    def release(self, token, amount):
        held = self._held.get(token, 0)
        if amount > held:
            raise ResourceError(f"releasing {amount} > held {held} for {token}")
        remaining = held - amount
        if remaining:
            self._held[token] = remaining
        else:
            self._held.pop(token, None)
        self.available += amount

    def in_use(self):
        return self.capacity - self.available
