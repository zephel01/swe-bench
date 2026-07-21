"""Rotate a log file into a chain of gzipped generations."""
from __future__ import annotations

import gzip
from pathlib import Path


def _gen_path(base: Path, index: int) -> Path:
    """Return the path for generation ``index`` of ``base``."""
    return base.with_name(f"{base.name}.{index}.gz")


def _compress(src: Path, dst: Path) -> None:
    """Gzip ``src`` into ``dst`` and remove the original file."""
    with src.open("rb") as f_in, gzip.open(dst, "wb") as f_out:
        f_out.writelines(f_in)
    src.unlink()


def _shift(base: Path, keep: int) -> None:
    """Shift existing generations one slot higher, dropping past ``keep``."""
    top = _gen_path(base, keep)
    if top.exists():
        top.unlink()
    for i in range(keep - 1, 0, -1):
        src = _gen_path(base, i)
        dst = _gen_path(base, i + 1)
        if src.exists():
            src.rename(dst)


def rotate(base_path: Path, keep: int = 5) -> None:
    """Rotate ``base_path`` into ``base_path.1.gz`` and shift older files."""
    base = Path(base_path)
    if not base.exists():
        return
    _compress(base, _gen_path(base, 1))
    _shift(base, keep)
