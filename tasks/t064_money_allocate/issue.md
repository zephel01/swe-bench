# Bug: allocated cents do not add back up to the total

`allocate(total_cents, weights)` splits an integer amount of cents across
several parts proportionally to `weights`, returning a list of integer cents.
The invariant that must always hold is `sum(allocate(t, w)) == t`.

Failing examples:

    allocate(100, [1, 1, 1])          # returns [33, 33, 33], sum 99, expected sum 100
    allocate(100, [1, 1, 1, 1, 1, 1]) # returns [17, 17, 17, 17, 17, 17], sum 102
    allocate(2000, [1, 1, 1])         # returns [667, 667, 667], sum 2001

Money is neither created nor destroyed: the parts must sum to exactly
`total_cents`, and each part must be within one cent of an even share.
Cleanly divisible cases such as `allocate(90, [1, 1, 1]) == [30, 30, 30]`
already work.
