"""Sort keys for rotated log file names."""
from __future__ import annotations


_PAD_WIDTH = 4


def generation_key(name: str) -> str:
    """Return a sortable key for a rotated log file name.

    Given a file name such as ``app.log.10.gz`` the returned string can
    be used as ``key=`` for :func:`sorted` to list generations from the
    newest to the oldest.
    """
    for part in name.split("."):
        if part.isdigit():
            return part.zfill(_PAD_WIDTH)
    return "0".zfill(_PAD_WIDTH)


def sort_generations(names: list[str]) -> list[str]:
    """Return ``names`` sorted by their generation key."""
    return sorted(names, key=generation_key)
