# Bug: expired reservations can still be confirmed, corrupting stock counts

The `Inventory` tracks `on_hand` stock and a `reserved` count. The invariant is
`reserved == sum of active reservation quantities`, `available() == on_hand -
reserved` (never negative), and `on_hand` only drops by the quantity of
*confirmed* reservations.

A reservation expires when the clock passes its deadline. Confirming a
reservation that is no longer active is supposed to be rejected.

Reproduce:
1. `a = reserve(30, ttl=5)` and `b = reserve(20, ttl=100)`.
2. `tick(10)` so that `a` expires.
3. `confirm(b)` (fine).
4. `confirm(a)`.

Observed at step 4:
- `confirm(a)` does not raise.
- `reserved` becomes `-30` (the expiry already subtracted a's 30, and confirm
  subtracts it again).
- `on_hand` drops to `50` for stock that was never actually sold.
- `available()` no longer equals `on_hand - reserved` in any meaningful way.

Expected: `confirm(a)` raises because `a` has expired; `reserved` stays `0`,
`on_hand` stays `80` (only `b` sold). Reserve/confirm within the deadline,
auto-expiry, and release all behave correctly.
