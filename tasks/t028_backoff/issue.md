# Bug: every backoff delay is one doubling too large

`backoff_schedule(2, 20, 1, "full")` returns `[(0, 4)]`, but the very first
attempt's delay ceiling should be the base value `2`, i.e. `[(0, 2)]`. Each
attempt's ceiling is doubled one step too early compared to what's expected.

The `full`/`equal` jitter bounds and the cap behaviour are otherwise correct.
