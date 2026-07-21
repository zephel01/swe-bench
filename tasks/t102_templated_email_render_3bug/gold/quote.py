"""Quote-level re-indentation for RFC 3676 style reply chains."""
from __future__ import annotations


def add_quote_level(text: str) -> str:
    """Return ``text`` with one additional level of ``>`` quoting."""
    out: list[str] = []
    for line in text.split("\n"):
        if line.startswith(">"):
            out.append(">" + line)
        elif not line:
            out.append(">")
        else:
            out.append("> " + line)
    return "\n".join(out)
