from backend import MemoryBackend
from serializer import dumps, loads


class TTLCache:
    def __init__(self, backend=None, clock=None):
        self.backend = backend or MemoryBackend()
        self.clock = clock or (lambda: 0.0)

    def put(self, key, value, ttl):
        expires = self.clock() + ttl
        self.backend.set(key, dumps({"v": value, "exp": expires}))

    def get(self, key):
        raw = self.backend.get(key)
        if raw is None:
            return None
        record = loads(raw)
        if record["exp"] <= self.clock():
            self.backend.delete(key)
            return None
        return record["v"]
