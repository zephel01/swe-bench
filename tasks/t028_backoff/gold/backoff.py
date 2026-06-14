"""指数バックオフのジッタ境界を計算する (乱数は使わず上下限のみ)."""

from __future__ import annotations


def backoff_schedule(
    base: float, cap: float, attempts: int, strategy: str = "full"
) -> list[tuple[float, float]]:
    """各試行 (1始まり) の遅延ジッタ境界 (low, high) のリストを返す。

    遅延の上限 = min(cap, base * 2**(attempt-1))。
    strategy="full": [0, delay] / strategy="equal": [delay/2, delay]。
    """
    if attempts < 1:
        raise ValueError("attempts must be >= 1")
    if base <= 0 or cap < base:
        raise ValueError("require base > 0 and cap >= base")
    out: list[tuple[float, float]] = []
    for n in range(1, attempts + 1):
        delay = min(cap, base * 2 ** (n - 1))
        if strategy == "full":
            out.append((0, delay))
        elif strategy == "equal":
            out.append((delay / 2, delay))
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")
    return out
