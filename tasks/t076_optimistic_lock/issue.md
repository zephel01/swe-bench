# Bug: commit_all is not atomic -- a late conflict leaves earlier writes applied

`Store.commit_all(changes)` is documented to apply several optimistic-locked
writes atomically: either every expected version matches and all writes take
effect, or nothing changes at all.

Reproduce:
1. `create("x", 1)`, `create("y", 2)`.
2. Read both to get `vx`, `vy`.
3. A concurrent writer does `update("y", vy, 99)`, bumping y's version so the
   caller's `vy` is now stale.
4. `commit_all([("x", vx, 10), ("y", vy, 20)])`.

Observed:
- `commit_all` raises `ConflictError` on `y` (expected), but `x` has already
  been changed to `10` and its version bumped.
- So a rolled-back batch left a partial write visible: `read("x")` is
  `(10, vx + 1)` instead of `(1, vx)`.

Expected: because one change in the batch conflicts, the whole batch is
rejected and no record is modified -- `x` stays `(1, vx)`. Single `update`
version checks and an all-valid `commit_all` both behave correctly.
