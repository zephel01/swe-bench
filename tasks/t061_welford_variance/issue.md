# Bug: sample variance collapses to a wrong value for large-offset data

`variance(values)` returns the sample variance (dividing by `n - 1`).
It is accurate for small numbers, but as soon as the data carries a large
constant offset the result is badly wrong.

Failing example:

    base = [1.0, 2.0, 3.0, 4.0, 5.0]          # sample variance is 2.5
    shifted = [x + 1e9 for x in base]         # same spread, just offset
    variance(shifted)   # returns 0.0, expected 2.5

The spread of `shifted` is identical to `base`, so the answer must still be
`2.5`. Small-magnitude inputs keep working; only the offset case breaks.
