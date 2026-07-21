"""Lenient KEY=VALUE config parser (no strict mode yet)."""
from __future__ import annotations


def parse(text: str) -> dict:
    """Parse a lenient KEY=VALUE config format and return a dict.

    Behavior:
      - blank lines and lines starting with '#' are ignored
      - '@unset KEY' removes KEY from the result if present
      - unknown '@directive' lines are silently ignored
      - 'KEY=VALUE' assigns (whitespace around '=' is trimmed);
        duplicate keys are last-wins
      - anything else is silently ignored
    """
    result: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("@"):
            body = line[1:].strip()
            parts = body.split(None, 1)
            name = parts[0] if parts else ""
            if name == "unset" and len(parts) == 2:
                result.pop(parts[1].strip(), None)
            continue
        if "=" in line:
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip()
            continue
    return result
