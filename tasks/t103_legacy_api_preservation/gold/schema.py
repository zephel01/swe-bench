"""Data classes shared by the search package.

The centrepiece is :class:`SearchRequest`: an immutable, hashable-free
value object that captures every input the search implementation needs.
Both the legacy ``search(q, filters)`` entry point and the new
``search(SearchRequest)`` entry point end up building one of these before
dispatching to the service layer, so there is exactly one internal
representation of a search request.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Optional


@dataclass(frozen=True)
class SearchRequest:
    """An immutable search request.

    Attributes:
        q: Full-text query string (may be empty to match all documents).
        filters: Mapping of ``field -> expected value`` equality filters.
        limit: Optional maximum number of results to return.
        offset: Optional number of results to skip before returning.
    """

    q: str
    filters: Mapping[str, Any] = field(default_factory=dict)
    limit: Optional[int] = None
    offset: Optional[int] = None

    def __post_init__(self) -> None:
        if not isinstance(self.q, str):
            raise TypeError(
                f"SearchRequest.q must be str, got {type(self.q).__name__}"
            )
        if self.limit is not None and self.limit < 0:
            raise ValueError("SearchRequest.limit must be non-negative")
        if self.offset is not None and self.offset < 0:
            raise ValueError("SearchRequest.offset must be non-negative")
