# Bug: minimum coin count is not actually minimal

`min_coins([1, 3, 4], 6)` returns `3`, but the amount 6 can be made with just
`2` coins. The function is supposed to return the fewest coins possible for any
coin set, and here it overshoots.

Impossible amounts still correctly return `-1`, and `0` returns `0`.
