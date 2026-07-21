"""Parser exception hierarchy (base + three specific subclasses)."""
from __future__ import annotations


class ParseError(Exception):
    """Base class for every parser error.

    Callers that want to catch any strict-mode failure can simply
    ``except ParseError:``; specific subclasses below let callers
    distinguish categories.
    """


class SyntaxError(ParseError):  # noqa: A001
    """Raised in strict mode for a line that is not a comment, blank,
    recognized directive, or a valid ``KEY=VALUE`` assignment."""


class DuplicateKeyError(ParseError):
    """Raised in strict mode when the same key is assigned more than once."""


class UnknownDirectiveError(ParseError):
    """Raised in strict mode when an ``@directive`` is not recognized."""
