"""HTTP-ish entry point (accepts int or str, normalizes to str)."""
from __future__ import annotations

from typing import Optional, Union

from repo import UserRepo
from service import UserService

IdLike = Union[int, str]


def _normalize_id(id: IdLike) -> str:
    """Coerce an incoming int or str id into the canonical str form."""
    if isinstance(id, bool) or not isinstance(id, (int, str)):
        raise TypeError(f"id must be int or str, got {type(id).__name__}")
    return str(id)


def make_api() -> "API":
    """Build a wired-up API with a fresh in-memory repository."""
    return API(UserService(UserRepo()))


class API:
    """Thin wrapper over UserService that speaks dict payloads."""

    def __init__(self, service: UserService) -> None:
        self.service = service

    def create(self, payload: dict) -> dict:
        id_str = _normalize_id(payload["id"])
        user = self.service.register(id_str, payload["name"], payload["email"])
        return {"id": user.id, "name": user.name, "email": user.email}

    def get(self, id: IdLike) -> Optional[dict]:
        id_str = _normalize_id(id)
        user = self.service.find(id_str)
        if user is None:
            return None
        return {"id": user.id, "name": user.name, "email": user.email}
