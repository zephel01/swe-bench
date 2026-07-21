"""Field-delimiter detection for CSV dialect inference."""
from __future__ import annotations

__all__ = ["detect_delimiter"]

_CANDIDATES = (',', ';', '\t', '|')


def detect_delimiter(sample: str, quotechar: str) -> str:
    """Return the most likely field delimiter in *sample*."""
    text = _strip_quoted(sample, quotechar)
    counts = {c: text.count(c) for c in _CANDIDATES}
    return max(counts, key=lambda c: counts[c])


def _strip_quoted(sample: str, quotechar: str) -> str:
    """Return *sample* with every quoted region removed."""
    out: list[str] = []
    in_quote = False
    for ch in sample:
        if ch == quotechar:
            in_quote = not in_quote
        elif not in_quote:
            out.append(ch)
    return ''.join(out)
