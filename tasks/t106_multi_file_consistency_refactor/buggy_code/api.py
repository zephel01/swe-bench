"""HTTP-ish entry point (forwards payload id verbatim)."""
from __future__ import annotations

from typing import Optional

from repo import UserRepo
from service import UserService


def make_api() -> "API":
    """Build a wired-up API with a fresh in-memory repository."""
    return API(UserService(UserRepo()))


class API:
    """Thin wrapper over UserService that speaks dict payloads."""

    def __init__(self, service: UserService) -> None:
        self.service = service

    def create(self, payload: dict) -> dict:
        id = payload["id"]
        user = self.service.register(id, payload["name"], payload["email"])
        return {"id": user.id, "name": user.name, "email": user.email}

    def get(self, id) -> Optional[dict]:
        user = self.service.find(id)
        if user is None:
            return None
        return {"id": user.id, "name": user.name, "email": user.email}
