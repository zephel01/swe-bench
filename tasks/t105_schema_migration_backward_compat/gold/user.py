"""User dataclass with split first/last name and backward-compatible property."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class User:
    first_name: str
    last_name: str

    @property
    def name(self) -> str:
        """Backward-compatible full-name accessor used by legacy call sites."""
        return f"{self.first_name} {self.last_name}".strip()
