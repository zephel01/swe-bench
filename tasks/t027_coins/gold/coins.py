"""最小硬貨枚数。任意の硬貨体系で最適 (動的計画法)."""

from __future__ import annotations


def min_coins(coins: list[int], amount: int) -> int:
    """amount を作る最小硬貨枚数を返す。作れなければ -1。"""
    if amount < 0:
        raise ValueError("amount must be non-negative")
    inf = amount + 1
    dp = [0] + [inf] * amount
    for a in range(1, amount + 1):
        for c in coins:
            if 0 < c <= a and dp[a - c] + 1 < dp[a]:
                dp[a] = dp[a - c] + 1
    return dp[amount] if dp[amount] != inf else -1
