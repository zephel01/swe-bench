"""会計用の金額計算ユーティリティ (float禁止・Decimalのみ)."""

from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_HALF_EVEN, Decimal

CENT = Decimal("0.01")


def round_money(amount, places: int = 2) -> Decimal:
    """金額を指定桁で丸める.

    会計規約により **銀行家の丸め (half-to-even)** を用いる。
    例: 0.125 -> 0.12, 0.025 -> 0.02 (5の手前が偶数なら切り捨て)。
    """
    q = Decimal(1).scaleb(-places)
    return Decimal(amount).quantize(q, rounding=ROUND_HALF_EVEN)


def allocate(total, weights: list) -> list[Decimal]:
    """total を weights 比で按分し、丸め後の合計が total に厳密一致する.

    最大剰余法: いったん切り捨て、余りのセントを端数の大きい順に配る。
    """
    if not weights:
        raise ValueError("weights must be non-empty")
    if any(Decimal(w) < 0 for w in weights):
        raise ValueError("weights must be non-negative")
    total = Decimal(total)
    wsum = sum(Decimal(w) for w in weights)
    if wsum == 0:
        raise ValueError("weights sum to zero")
    raw = [total * Decimal(w) / wsum for w in weights]
    floors = [r.quantize(CENT, rounding=ROUND_DOWN) for r in raw]
    leftover = total - sum(floors)
    cents = int((leftover / CENT).to_integral_value(rounding=ROUND_HALF_EVEN))
    order = sorted(
        range(len(weights)),
        key=lambda i: (raw[i] - floors[i], Decimal(weights[i])),
        reverse=True,
    )
    result = list(floors)
    for k in range(cents):
        result[order[k]] += CENT
    return result
