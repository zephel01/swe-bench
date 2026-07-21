"""Domain model for the user module (str-unified)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    """A user record with a string identifier."""
    id: str
    name: str
    email: str
