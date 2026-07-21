"""User dataclass (legacy version with single `name` field)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    name: str
