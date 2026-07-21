"""Size-limited writer used as the first stage of the log rotator."""
from __future__ import annotations

from pathlib import Path


class SizeLimitedWriter:
    """Append text messages to a file and track how many bytes we wrote.

    The writer is intentionally byte-oriented: callers configure a
    ``max_bytes`` threshold and ask :meth:`should_rotate` to decide when
    the accompanying rotator should be invoked.
    """

    def __init__(self, path: Path, max_bytes: int) -> None:
        self.path = Path(path)
        self.max_bytes = max_bytes
        self._size = 0

    def write(self, msg: str) -> None:
        """Append ``msg`` and a trailing newline to the underlying file."""
        line = msg + "\n"
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(line)
        self._size += len(line.encode("utf-8"))

    def current_size(self) -> int:
        """Return the number of bytes accounted for in the current file."""
        return self._size

    def should_rotate(self) -> bool:
        """Return ``True`` once the accounted size has reached the limit."""
        return self._size >= self.max_bytes

    def reset(self) -> None:
        """Truncate the underlying file and reset the byte counter."""
        self.path.write_text("", encoding="utf-8")
        self._size = 0
