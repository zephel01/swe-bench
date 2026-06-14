"""SemVer 2.0.0 のパースと優先順位比較 (プレリリース対応)."""

from __future__ import annotations

import re
from functools import cmp_to_key

_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)(?:-([0-9A-Za-z.-]+))?$")


def parse(version: str) -> tuple[int, int, int, tuple[str, ...]]:
    m = _RE.match(version.strip())
    if not m:
        raise ValueError(f"invalid version: {version!r}")
    pre = tuple(m.group(4).split(".")) if m.group(4) else ()
    return int(m.group(1)), int(m.group(2)), int(m.group(3)), pre


def _cmp_ident(a: str, b: str) -> int:
    an, bn = a.isdigit(), b.isdigit()
    if an and bn:
        return (int(a) > int(b)) - (int(a) < int(b))
    if an != bn:
        return -1 if an else 1  # 数値識別子は英数字識別子より小さい
    return (a > b) - (a < b)


def _cmp_pre(pa: tuple[str, ...], pb: tuple[str, ...]) -> int:
    if pa == pb:
        return 0
    # プレリリース無しは有りより「大きい」(優先順位が高い)
    if not pa:
        return 1
    if not pb:
        return -1
    for x, y in zip(pa, pb, strict=False):
        c = _cmp_ident(x, y)
        if c:
            return c
    return (len(pa) > len(pb)) - (len(pa) < len(pb))


def compare(a: str, b: str) -> int:
    pa, pb = parse(a), parse(b)
    core = (pa[:3] > pb[:3]) - (pa[:3] < pb[:3])
    if core:
        return core
    return _cmp_pre(pa[3], pb[3])


def sort_versions(versions: list[str]) -> list[str]:
    return sorted(versions, key=cmp_to_key(compare))
