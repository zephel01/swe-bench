"""Schema module for the search package.

Placeholder for future request/response dataclasses.  For now the package
only has a positional legacy API so nothing lives here yet.
"""
from __future__ import annotations

# NOTE: A future refactor will introduce a ``SearchRequest`` dataclass so
# that both the legacy ``search(q, filters)`` form and a new
# ``search(SearchRequest(...))`` form share a single internal
# representation.  Until then this module is intentionally empty.
