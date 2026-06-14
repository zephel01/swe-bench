"""ジャーナル付きインメモリKVストア (begin/commit/rollback, ネスト可)."""

from __future__ import annotations

from journal import MISSING, Journal


class KVStore:
    def __init__(self) -> None:
        self._data: dict = {}
        self._journal = Journal()

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value) -> None:
        self._journal.record(key, self._data.get(key, MISSING))
        self._data[key] = value

    def delete(self, key) -> None:
        self._journal.record(key, self._data.get(key, MISSING))
        self._data.pop(key, None)

    def begin(self) -> None:
        self._journal.begin()

    def commit(self) -> None:
        self._journal.commit()

    def rollback(self) -> None:
        undo = self._journal.rollback()
        for key, old in undo.items():
            if old is MISSING:
                self._data.pop(key, None)
            else:
                self._data[key] = old
