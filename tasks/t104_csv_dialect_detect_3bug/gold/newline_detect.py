"""Line-terminator detection for CSV dialect inference."""
from __future__ import annotations

__all__ = ["detect_newline"]


def detect_newline(sample: str) -> str:
    """Return the dominant line terminator in *sample*."""
    crlf = sample.count('\r\n')
    lf = sample.count('\n') - crlf
    cr = sample.count('\r') - crlf
    if lf >= cr and lf >= crlf:
        return '\n'
    if crlf >= cr:
        return '\r\n'
    return '\r'
