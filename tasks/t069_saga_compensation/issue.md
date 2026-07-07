# Bug: a failed compensation strands earlier saga steps

We run a saga of steps, each of which acquires from a shared resource `Pool`
and has a matching compensation that releases it. When a later step's action
fails, the runner is supposed to compensate every completed step and leave the
pool fully released.

This works as long as the compensations all succeed. But when one completed
step's compensation raises (we simulate an unreachable remote compensator),
things go wrong:

Reproduce:
1. Add steps `a` (acquire 10), `b` (acquire 20), `c` (acquire 30), then a step
   `d` whose action raises `ValueError`.
2. Make step `b`'s compensation raise `RuntimeError`.
3. Run the saga.

Observed:
- The exception that propagates out of `run()` is the `RuntimeError` from b's
  compensation, not the original `ValueError` from d.
- `pool.in_use()` is `30`, not `20`: step `a` was never compensated, so its
  10 units plus b's leaked 20 remain held.
- `runner.comp_failures` is empty, so nothing recorded which compensation
  failed.

Expected: b's failed compensation is recorded, a and c are still released
(`in_use() == 20`), and the original `ValueError` propagates.
