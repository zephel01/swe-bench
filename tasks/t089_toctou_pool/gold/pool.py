import threading


class ResourcePool:
    def __init__(self, ids):
        self._free = list(ids)
        self._in_use = set()
        self._lock = threading.Lock()

    def allocate(self):
        with self._lock:
            if not self._free:
                return None
            rid = self._free[0]
            self._free.remove(rid)
            self._in_use.add(rid)
            return rid

    def release(self, rid):
        with self._lock:
            self._in_use.discard(rid)
            self._free.append(rid)
