# Bug: floating-point sum drifts from the true value

`total(values)` loses precision when summing many terms of very different
magnitudes. For example `total([1.0, 1e16, 1.0, -1e16])` returns `0.0` instead
of `2.0`, and summing ten million tiny values plus a large +/- pair drifts well
beyond rounding. Small sums are fine.

Use a compensated summation (Kahan-style or equivalent) so the result stays
accurate. It must still handle a million values quickly.
