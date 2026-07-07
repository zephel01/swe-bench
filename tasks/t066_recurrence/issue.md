# Bug: integral(n) returns nonsense once n grows past ~15

`integral(n)` computes the definite integral

    E_n = integral from 0 to 1 of x**n * e**(x - 1) dx

for a non-negative integer `n`. These integrals form a slowly decreasing
sequence of small positive numbers (for example `E_25` is about `0.03709`).

Failing examples:

    integral(25)   # returns about 1.93e8, expected about 0.03709
    integral(30)   # returns about -3.3e15, expected about 0.03128

For large `n` the function returns huge and even negative values, which is
impossible: `0 < E_n < 1` and the sequence is strictly decreasing. Small `n`
(say `n <= 8`) is accurate.
