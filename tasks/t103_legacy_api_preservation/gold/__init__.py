"""Public exports for the search package.

The package exposes:

* :class:`SearchRequest` -- the canonical, immutable request object that
  gathers a query string, an optional mapping of filters, and optional
  ``limit`` / ``offset`` values for pagination.
* :func:`search` -- the polymorphic entry point.  It accepts either a
  :class:`SearchRequest` (preferred) or the historical ``(q, filters)``
  pair (kept working for backward compatibility with existing callers).
* :class:`LegacySearchDeprecated` -- a dedicated
  :class:`DeprecationWarning` subclass emitted every time the legacy
  call form is used.  Downstream projects can install a
  ``filterwarnings("error", ..., LegacySearchDeprecated)`` filter in
  their test suite to hard-fail on any remaining legacy call sites.
"""
from __future__ import annotations

from api import LegacySearchDeprecated, search
from schema import SearchRequest

__all__ = [
    "LegacySearchDeprecated",
    "SearchRequest",
    "search",
]

__version__ = "1.0.0"


def public_symbols() -> tuple[str, ...]:
    """Return the tuple of publicly exported symbol names."""
    return tuple(__all__)
