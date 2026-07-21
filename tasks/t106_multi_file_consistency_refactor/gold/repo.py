"""In-memory repository for User records (str-keyed with type checks)."""
from __future__ import annotations

from typing import Optional

from model import User


class UserRepo:
    """A tiny in-memory dictionary-backed repository, str-keyed."""

    def __init__(self) -> None:
        self._store: dict[str, User] = {}

    def save(self, user: User) -> None:
        if not isinstance(user.id, str):
            raise TypeError(
                f"user.id must be str, got {type(user.id).__name__}"
            )
        self._store[user.id] = user

    def get(self, id: str) -> Optional[User]:
        if not isinstance(id, str):
            raise TypeError(f"id must be str, got {type(id).__name__}")
        return self._store.get(id)

    def exists(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError(f"id must be str, got {type(id).__name__}")
        return id in self._store
