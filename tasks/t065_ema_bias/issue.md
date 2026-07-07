# Bug: exponential moving average is biased toward zero at the start

`ema(values, alpha)` returns a list the same length as `values`, where each
output is the exponentially weighted average of every sample seen so far
(the most recent sample has weight proportional to `alpha`, older ones decay
by `1 - alpha`). It must be a true weighted average of the samples.

Failing examples:

    ema([10.0, 10.0, 10.0, 10.0, 10.0], 0.5)
    # returns [5.0, 7.5, 8.75, 9.375, 9.6875]
    # expected [10.0, 10.0, 10.0, 10.0, 10.0]

    ema([1.0, 3.0], 0.5)
    # returns [0.5, 1.75]
    # expected [1.0, 2.3333333333333335]

For a constant input every output must equal that constant, and the very first
output must equal the first sample. The early values are being dragged toward
zero because an empty history is treated as if it held a real zero sample.
