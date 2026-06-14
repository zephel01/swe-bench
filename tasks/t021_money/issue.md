# Bug: monetary amounts are rounded incorrectly at the half-cent

Some rounded amounts don't match what our accounting reconciliation expects:

- `round_money(Decimal("0.125"))` returns `0.13` (expected `0.12`)
- `round_money(Decimal("0.025"))` returns `0.03` (expected `0.02`)
- `round_money(Decimal("0.045"))` returns `0.05` (expected `0.04`)
- `round_money(Decimal("1.2345"), 3)` returns `1.235` (expected `1.234`)

Other amounts round fine, and `allocate()` still sums exactly to its total.
