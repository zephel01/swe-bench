# Bug: a failed transition side effect still advances the state machine

`Machine.fire(event, action)` validates the event, runs the side effect, and
records the transition. If the side effect fails, the machine is supposed to
stay exactly where it was: the transition never happened.

Reproduce:
1. Fresh machine (state `"created"`).
2. `fire("pay", action=decline)` where `decline` raises `PaymentDeclined`
   before touching the ledger.

Observed:
- The `PaymentDeclined` propagates (expected), but the machine is now in state
  `"paid"` and `history` contains the `pay` transition.
- Because it believes it is `"paid"`, `fire("ship")` now succeeds -- an order
  that was never paid can be shipped.
- A later `rewind(1)` runs the `pay` compensation and refunds `100` for a
  payment that never happened, driving `ledger` to `-100`.

Expected: after the declined payment the machine is still `"created"` with an
empty history, `fire("ship")` raises `InvalidTransition`, and `rewind` has
nothing to compensate. The happy path (successful pay/ship then rewind) and
guard rejection of illegal transitions both behave correctly.
