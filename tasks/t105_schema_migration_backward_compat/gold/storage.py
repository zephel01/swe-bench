"""Persistence for User records with legacy-schema migration."""
from __future__ import annotations

import json
from pathlib import Path

from migration import migrate_legacy
from user import User


def save_user(user: User, path: Path) -> None:
    """Persist a user in the new schema (first_name / last_name)."""
    data = {"first_name": user.first_name, "last_name": user.last_name}
    Path(path).write_text(json.dumps(data), encoding="utf-8")


def load_user(path: Path) -> User:
    """Load a user, transparently migrating legacy single-`name` records."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    record = migrate_legacy(raw)
    return User(first_name=record["first_name"], last_name=record["last_name"])
