"""最小硬貨枚数。任意の硬貨体系で最適 (動的計画法)."""

from __future__ import annotations


def min_coins(coins: list[int], amount: int) -> int:
    """amount を作る最小硬貨枚数を返す。作れなければ -1。"""
    if amount < 0:
        raise ValueError("amount must be non-negative")
    count = 0
    for c in sorted(coins, reverse=True):
        while c > 0 and amount >= c:
            amount -= c
            count += 1
    return count if amount == 0 else -1
