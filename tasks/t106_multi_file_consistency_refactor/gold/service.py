"""Business-logic layer for user records (str-typed)."""
from __future__ import annotations

from typing import Optional

from model import User
from repo import UserRepo


class UserService:
    """Register / look up users. Delegates persistence to UserRepo."""

    def __init__(self, repo: UserRepo) -> None:
        self.repo = repo

    def register(self, id: str, name: str, email: str) -> User:
        if not isinstance(id, str):
            raise TypeError(f"id must be str, got {type(id).__name__}")
        user = User(id=id, name=name, email=email)
        self.repo.save(user)
        return user

    def find(self, id: str) -> Optional[User]:
        if not isinstance(id, str):
            raise TypeError(f"id must be str, got {type(id).__name__}")
        return self.repo.get(id)

    def is_registered(self, id: str) -> bool:
        if not isinstance(id, str):
            raise TypeError(f"id must be str, got {type(id).__name__}")
        return self.repo.exists(id)
