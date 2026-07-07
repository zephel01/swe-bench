"""A record store with optimistic concurrency control.

Every record carries a version. A write must present the version it expects to
overwrite; if that does not match the current version, the write is rejected as
a conflict. A successful write bumps the version by exactly one.

`commit_all` applies several writes atomically: either every expected version
matches and all writes take effect, or nothing changes at all. A partial commit
-- some records written, some not -- must never be observable.
"""


class ConflictError(Exception):
    pass


class Store:
    def __init__(self):
        self._records = {}     # key -> {"value", "version"}

    def create(self, key, value):
        self._records[key] = {"value": value, "version": 1}

    def read(self, key):
        r = self._records[key]
        return r["value"], r["version"]

    def update(self, key, expected_version, value):
        r = self._records[key]
        if r["version"] != expected_version:
            raise ConflictError(f"stale version for {key!r}")
        r["value"] = value
        r["version"] += 1

    def commit_all(self, changes):
        changes = list(changes)
        for key, expected_version, _value in changes:
            if self._records[key]["version"] != expected_version:
                raise ConflictError(f"stale version for {key!r}")
        for key, _expected_version, value in changes:
            r = self._records[key]
            r["value"] = value
            r["version"] += 1
