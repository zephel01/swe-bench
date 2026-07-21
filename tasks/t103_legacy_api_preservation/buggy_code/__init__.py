"""Public exports for the search package (legacy version).

Only the legacy ``search`` symbol is exported.  A future revision will
also expose ``SearchRequest`` and ``LegacySearchDeprecated`` here.
"""
from __future__ import annotations

from api import search

__all__ = ["search"]

__version__ = "0.9.0"
