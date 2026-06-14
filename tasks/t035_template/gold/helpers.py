"""補助関数 (テンプレート整形ユーティリティ)."""

from __future__ import annotations


def truncate(text: str, limit: int) -> str:
    if limit < 0:
        raise ValueError("limit must be non-negative")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def repeat(text: str, times: int) -> str:
    return text * max(0, times)
