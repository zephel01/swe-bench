# Bug: log_sum_exp crashes / returns nonsense for large or very negative inputs

`log_sum_exp(xs)` must return `log(sum(exp(x) for x in xs))`. It works for
small inputs but blows up once the magnitudes grow.

Failing examples:

    log_sum_exp([1000.0, 1000.0])     # raises OverflowError, expected 1000 + log(2)
    log_sum_exp([-1000.0, -1000.0])   # raises "math domain error", expected -1000 + log(2)
    log_sum_exp([710.0])              # raises OverflowError, expected 710.0

Mathematically all three answers are perfectly ordinary finite numbers. Small
inputs such as `log_sum_exp([0.0, 0.0]) == log(2)` already behave correctly.
