"""Field-delimiter detection for CSV dialect inference."""
from __future__ import annotations

__all__ = ["detect_delimiter"]

_CANDIDATES = (',', ';', '\t', '|')


def detect_delimiter(sample: str, quotechar: str) -> str:
    """Return the most likely field delimiter in *sample*."""
    text = sample
    counts = {c: text.count(c) for c in _CANDIDATES}
    return max(counts, key=lambda c: counts[c])
