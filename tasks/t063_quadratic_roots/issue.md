# Bug: one root of the quadratic is lost when b dominates a and c

`solve(a, b, c)` returns the two real roots of `a*x**2 + b*x + c = 0`.
For well-separated roots it silently produces a garbage value for the root that
is small in magnitude.

Failing example:

    r = solve(1.0, 1e10, 1.0)
    # the exact roots multiply to c/a = 1.0
    r[0] * r[1]     # returns 0.0, expected 1.0
    min(r, key=abs) # returns 0.0, expected about -1e-10

The product of the two roots must equal `c / a`. Textbook cases such as
`solve(1.0, -3.0, 2.0) == (2.0, 1.0)` are unaffected.
