"""購読情報."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Subscription:
    sub_id: int
    priority: int
    handler: object
