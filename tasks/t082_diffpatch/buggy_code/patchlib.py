"""Rendering a context view around a changed region of text."""

from hunks import context_window
from textio import from_lines, to_lines


def context_view(text, start, end, context):
    """Return the text block around change ``[start, end)`` with context lines."""
    lines = to_lines(text)
    lo, hi = context_window(len(lines), start, end, context)
    return from_lines(lines[lo:hi])
