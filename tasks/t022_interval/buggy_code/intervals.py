"""閉区間 [start, end] (整数) の集合。重なり・隣接は自動マージ。"""

from __future__ import annotations


class IntervalSet:
    def __init__(self) -> None:
        self._iv: list[tuple[int, int]] = []

    def add(self, start: int, end: int) -> None:
        if start > end:
            raise ValueError("start must be <= end")
        lo, hi = start, end
        rest: list[tuple[int, int]] = []
        for s, e in self._iv:
            # 整数の閉区間なので「隙間が1以上」離れていなければ隣接としてマージ
            if e < lo or s > hi:
                rest.append((s, e))
            else:
                lo, hi = min(lo, s), max(hi, e)
        rest.append((lo, hi))
        rest.sort()
        self._iv = rest

    def remove(self, start: int, end: int) -> None:
        if start > end:
            raise ValueError("start must be <= end")
        rest: list[tuple[int, int]] = []
        for s, e in self._iv:
            if e < start or s > end:
                rest.append((s, e))
                continue
            if s < start:
                rest.append((s, start - 1))
            if e > end:
                rest.append((end + 1, e))
        rest.sort()
        self._iv = rest

    def contains(self, x: int) -> bool:
        return any(s <= x <= e for s, e in self._iv)

    def total_length(self) -> int:
        return sum(e - s + 1 for s, e in self._iv)

    def intervals(self) -> list[tuple[int, int]]:
        return list(self._iv)
