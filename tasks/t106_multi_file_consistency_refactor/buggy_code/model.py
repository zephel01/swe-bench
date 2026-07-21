"""Domain model for the user module."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    """A user record."""
    id: int
    name: str
    email: str
