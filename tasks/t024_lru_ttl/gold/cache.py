"""TTL付きLRUキャッシュ。clock は0引数のcallableで現在時刻を返す."""

from __future__ import annotations

from collections import OrderedDict


class LRUTTLCache:
    def __init__(self, capacity: int, ttl: float, clock) -> None:
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        if ttl <= 0:
            raise ValueError("ttl must be positive")
        self.capacity = capacity
        self.ttl = ttl
        self._clock = clock
        self._data: OrderedDict[object, tuple[object, float]] = OrderedDict()

    def _expired(self, expiry: float, now: float) -> bool:
        # 区間 [t, t+ttl) で有効。期限ちょうど (now == expiry) は失効。
        return now >= expiry

    def get(self, key):
        if key not in self._data:
            return None
        value, expiry = self._data[key]
        now = self._clock()
        if self._expired(expiry, now):
            del self._data[key]
            return None
        self._data.move_to_end(key)
        return value

    def put(self, key, value) -> None:
        now = self._clock()
        if key in self._data:
            self._data.move_to_end(key)
        self._data[key] = (value, now + self.ttl)
        self._evict(now)

    def _evict(self, now: float) -> None:
        # まず失効分を掃除してから容量超過分をLRUで落とす
        for k in list(self._data):
            _, expiry = self._data[k]
            if self._expired(expiry, now):
                del self._data[k]
        while len(self._data) > self.capacity:
            self._data.popitem(last=False)

    def __len__(self) -> int:
        return len(self._data)
