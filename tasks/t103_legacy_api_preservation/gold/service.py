"""Business logic for search.

The service takes a :class:`schema.SearchRequest` and returns a list of
matching item dictionaries.  It is the single implementation both the
legacy and the new public API delegate to.
"""
from __future__ import annotations

from typing import Any, Dict, List

from schema import SearchRequest

_DATA: List[Dict[str, Any]] = [
    {"id": 1, "title": "python guide", "category": "docs", "lang": "en"},
    {"id": 2, "title": "python cookbook", "category": "book", "lang": "en"},
    {"id": 3, "title": "rust guide", "category": "docs", "lang": "en"},
    {"id": 4, "title": "python入門", "category": "book", "lang": "ja"},
    {"id": 5, "title": "go primer", "category": "docs", "lang": "en"},
]


class SearchService:
    """Executes a :class:`SearchRequest` against a fixed in-memory corpus."""

    def __init__(self, data: List[Dict[str, Any]] | None = None) -> None:
        self._data: List[Dict[str, Any]] = data if data is not None else _DATA

    def execute(self, req: SearchRequest) -> List[Dict[str, Any]]:
        needle = req.q.lower()
        results = [
            item for item in self._data
            if needle in item.get("title", "").lower()
        ]
        for key, value in req.filters.items():
            results = [item for item in results if item.get(key) == value]
        if req.offset is not None:
            results = results[req.offset:]
        if req.limit is not None:
            results = results[: req.limit]
        return results


_default_service = SearchService()


def execute_search(req: SearchRequest) -> List[Dict[str, Any]]:
    """Module-level convenience for the default in-memory service."""
    return _default_service.execute(req)
