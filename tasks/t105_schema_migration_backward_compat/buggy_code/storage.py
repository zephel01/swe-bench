"""Persistence for User records (legacy version)."""
from __future__ import annotations

import json
from pathlib import Path

from user import User


def save_user(user: User, path: Path) -> None:
    """Persist a user in the legacy single-`name` schema."""
    data = {"name": user.name}
    Path(path).write_text(json.dumps(data), encoding="utf-8")


def load_user(path: Path) -> User:
    """Load a user from the legacy single-`name` schema only."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return User(name=data["name"])
