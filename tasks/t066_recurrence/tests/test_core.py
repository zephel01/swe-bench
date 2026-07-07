import math

from recurrence import integral


def _reference(n):
    from decimal import Decimal, getcontext
    getcontext().prec = 60
    e = Decimal(1) - 1 / Decimal(1).exp()
    for k in range(1, n + 1):
        e = 1 - Decimal(k) * e
    return float(e)


def test_e0():
    assert abs(integral(0) - (1.0 - 1.0 / math.e)) < 1e-12


def test_small_values_accurate():
    for n in (1, 2, 5, 8):
        assert abs(integral(n) - _reference(n)) < 1e-9


def test_first_value_range():
    assert 0.0 < integral(3) < 1.0
