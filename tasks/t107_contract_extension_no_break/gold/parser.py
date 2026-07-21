"""KEY=VALUE config parser with lenient (default) and strict modes."""
from __future__ import annotations

from exceptions import DuplicateKeyError, SyntaxError, UnknownDirectiveError


def parse(text: str, strict: bool = False) -> dict:
    """Parse a KEY=VALUE config text and return a dict.

    Loose mode (``strict=False``, the default) preserves the historical
    behavior: unknown directives, malformed lines and duplicate keys
    are silently accepted (duplicates are last-wins).

    Strict mode (``strict=True``) raises a specific ``ParseError``
    subclass for each category of problem.
    """
    result: dict[str, str] = {}
    for lineno, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            body = line[1:].strip()
            parts = body.split(None, 1)
            name = parts[0] if parts else ""
            if name == "unset":
                if len(parts) == 2:
                    result.pop(parts[1].strip(), None)
                elif strict:
                    raise SyntaxError(
                        f"line {lineno}: @unset requires a key"
                    )
                continue
            if strict:
                raise UnknownDirectiveError(
                    f"line {lineno}: unknown directive @{name}"
                )
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if strict and key in result:
                raise DuplicateKeyError(
                    f"line {lineno}: duplicate key {key!r}"
                )
            result[key] = value
            continue
        if strict:
            raise SyntaxError(
                f"line {lineno}: malformed line: {raw!r}"
            )
    return result
