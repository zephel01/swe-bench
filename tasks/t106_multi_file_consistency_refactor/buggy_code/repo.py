"""In-memory repository for User records (int-keyed)."""
from __future__ import annotations

from typing import Optional

from model import User


class UserRepo:
    """A tiny in-memory dictionary-backed repository."""

    def __init__(self) -> None:
        self._store: dict[int, User] = {}

    def save(self, user: User) -> None:
        self._store[user.id] = user

    def get(self, id: int) -> Optional[User]:
        return self._store.get(id)

    def exists(self, id: int) -> bool:
        return id in self._store
