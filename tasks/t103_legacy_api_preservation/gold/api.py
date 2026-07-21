"""Public API for the search package.

Exposes a single polymorphic :func:`search` symbol that accepts either
the historical ``(q, filters)`` pair or a new :class:`SearchRequest`
object.  The legacy form is kept working so existing call sites don't
break, but it emits a :class:`LegacySearchDeprecated` warning so we can
track and eventually remove those call sites.
"""
from __future__ import annotations

import warnings
from typing import Any, Dict, List, Mapping, Optional, Union, overload

from schema import SearchRequest
from service import execute_search


class LegacySearchDeprecated(DeprecationWarning):
    """Emitted when ``search`` is called with the legacy ``(q, filters)`` form."""


_LEGACY_MESSAGE = (
    "search(q, filters) is deprecated; use search(SearchRequest(...)) instead."
)


@overload
def search(query: SearchRequest) -> List[Dict[str, Any]]: ...
@overload
def search(
    query: str,
    filters: Optional[Mapping[str, Any]] = ...,
) -> List[Dict[str, Any]]: ...


def search(
    query: Union[str, SearchRequest],
    filters: Optional[Mapping[str, Any]] = None,
) -> List[Dict[str, Any]]:
    """Search the catalog.

    Accepts either a :class:`SearchRequest` (preferred) or the historical
    ``(q, filters)`` pair.  Both forms delegate to the same service.
    """
    if isinstance(query, SearchRequest):
        if filters is not None:
            raise TypeError(
                "filters must not be passed together with a SearchRequest; "
                "put the filters inside the SearchRequest instead."
            )
        req = query
    elif isinstance(query, str):
        warnings.warn(
            _LEGACY_MESSAGE,
            LegacySearchDeprecated,
            stacklevel=2,
        )
        req = SearchRequest(
            q=query,
            filters=dict(filters) if filters is not None else {},
        )
    else:
        raise TypeError(
            f"search() query must be str or SearchRequest, "
            f"got {type(query).__name__}"
        )
    return execute_search(req)
