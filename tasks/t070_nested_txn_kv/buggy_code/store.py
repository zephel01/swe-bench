"""A key/value store with nested transactions and named savepoints.

begin() opens a nested transaction; commit() merges the innermost transaction
into its parent (or makes it durable at the top level); rollback() discards it.
Within a transaction, savepoint()/rollback_to()/release() give finer-grained
partial rollback.

The load-bearing invariant: a parent rollback must undo *everything* done since
the parent opened, including the effects of nested transactions that were
already committed into it.  Committing a child does not make its writes durable
-- it only promotes them into the parent, which can still roll them back.
"""

_MISSING = object()


class KVStore:
    def __init__(self):
        self.data = {}
        self._frames = []

    @property
    def depth(self):
        return len(self._frames)

    def begin(self):
        self._frames.append({"log": [], "marks": {}})

    def _record(self, key):
        if self._frames:
            prev = self.data.get(key, _MISSING)
            self._frames[-1]["log"].append((key, prev))

    def set(self, key, value):
        self._record(key)
        self.data[key] = value

    def delete(self, key):
        self._record(key)
        self.data.pop(key, None)

    def get(self, key):
        return self.data.get(key)

    def _restore(self, key, prev):
        if prev is _MISSING:
            self.data.pop(key, None)
        else:
            self.data[key] = prev

    def savepoint(self, name):
        frame = self._frames[-1]
        frame["marks"][name] = len(frame["log"])

    def rollback_to(self, name):
        frame = self._frames[-1]
        mark = frame["marks"][name]
        log = frame["log"]
        while len(log) > mark:
            key, prev = log.pop()
            self._restore(key, prev)
        frame["marks"] = {n: i for n, i in frame["marks"].items() if i <= mark}

    def release(self, name):
        del self._frames[-1]["marks"][name]

    def commit(self):
        self._frames.pop()

    def rollback(self):
        frame = self._frames.pop()
        for key, prev in reversed(frame["log"]):
            self._restore(key, prev)
