"""Parser exception hierarchy (base class only in this version)."""
from __future__ import annotations


class ParseError(Exception):
    """Base class for parser errors.

    The current parser does not actually raise this — it is exported
    as part of the public API for future use.
    """
