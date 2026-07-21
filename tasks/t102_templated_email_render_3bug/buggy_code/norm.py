"""Body normalization: line-end whitespace, newline style, trailing NL."""
from __future__ import annotations


def normalize_body(text: str) -> str:
    """Return the canonical form of a plain-text mail body."""
    lines = text.split("\n")
    cleaned = [line.rstrip() for line in lines]
    body = "\n".join(cleaned)
    if body and not body.endswith("\n"):
        body += "\n"
    return body
