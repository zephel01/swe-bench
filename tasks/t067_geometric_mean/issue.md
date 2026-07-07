# Bug: geometric_mean overflows or underflows for large/small magnitudes

`geometric_mean(values)` returns the geometric mean of a list of positive
numbers (the n-th root of their product). It is correct for ordinary numbers
but breaks when the magnitudes are extreme.

Failing examples:

    geometric_mean([1e200, 1e200, 1e200, 1e200, 1e200])
    # returns inf, expected 1e200

    geometric_mean([1e-200] * 5)
    # returns 0.0, expected 1e-200

The geometric mean of five copies of `1e200` is exactly `1e200`; the true
product `1e1000` overflows a float even though the answer is perfectly
representable. The same happens toward zero for tiny inputs. Ordinary cases
like `geometric_mean([1.0, 2.0, 4.0]) == 2.0` already work.
