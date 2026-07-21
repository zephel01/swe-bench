"""Business-logic layer for user records (unannotated ids)."""
from __future__ import annotations

from typing import Optional

from model import User
from repo import UserRepo


class UserService:
    """Register / look up users. Delegates persistence to UserRepo."""

    def __init__(self, repo: UserRepo) -> None:
        self.repo = repo

    def register(self, id, name: str, email: str) -> User:
        user = User(id=id, name=name, email=email)
        self.repo.save(user)
        return user

    def find(self, id) -> Optional[User]:
        return self.repo.get(id)

    def is_registered(self, id) -> bool:
        return self.repo.exists(id)
