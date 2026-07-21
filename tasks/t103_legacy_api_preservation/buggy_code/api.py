"""Public API for the search package (legacy version).

Only the historical ``search(q, filters)`` form is implemented here.
A new object-oriented form is planned but not yet wired up.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping, Optional

from service import execute_legacy_search


def search(
    q: str,
    filters: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search the catalog with a query string and optional filters.

    Legacy signature: takes a bare string plus a mapping of equality
    filters.  Returns a list of matching item dictionaries.
    """
    return execute_legacy_search(q, filters if filters is not None else {})
