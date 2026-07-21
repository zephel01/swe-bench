"""Quote-character detection for CSV dialect inference."""
from __future__ import annotations

__all__ = ["detect_quotechar"]


def detect_quotechar(sample: str) -> str:
    """Return the quote character used in *sample*."""
    candidates = ['"', "'"]
    counts = {c: sample.count(c) for c in candidates}
    return max(counts, key=lambda c: counts[c])
