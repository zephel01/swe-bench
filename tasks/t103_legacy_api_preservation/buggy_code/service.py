"""Business logic for search.

This module owns the actual search implementation.  It is intentionally
decoupled from the public API surface in ``api.py`` so we can swap the
implementation later without breaking callers.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

_DATA: List[Dict[str, Any]] = [
    {"id": 1, "title": "python guide", "category": "docs", "lang": "en"},
    {"id": 2, "title": "python cookbook", "category": "book", "lang": "en"},
    {"id": 3, "title": "rust guide", "category": "docs", "lang": "en"},
    {"id": 4, "title": "python入門", "category": "book", "lang": "ja"},
    {"id": 5, "title": "go primer", "category": "docs", "lang": "en"},
]


def execute_legacy_search(
    q: str,
    filters: Mapping[str, Any],
) -> List[Dict[str, Any]]:
    """Run a legacy-style search.

    Case-insensitive substring match on ``title``, then apply every
    ``key == value`` constraint in ``filters``.
    """
    needle = q.lower()
    results = [
        item for item in _DATA if needle in item.get("title", "").lower()
    ]
    for key, value in filters.items():
        results = [item for item in results if item.get(key) == value]
    return results
