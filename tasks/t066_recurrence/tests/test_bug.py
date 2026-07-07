from recurrence import integral


def _reference(n):
    from decimal import Decimal, getcontext
    getcontext().prec = 60
    e = Decimal(1) - 1 / Decimal(1).exp()
    for k in range(1, n + 1):
        e = 1 - Decimal(k) * e
    return float(e)


def test_large_n_accurate():
    for n in (20, 25, 30):
        assert abs(integral(n) - _reference(n)) < 1e-9


def test_sequence_bounded_and_decreasing():
    vals = [integral(n) for n in range(40)]
    for a, b in zip(vals, vals[1:]):
        assert 0.0 < b < a
