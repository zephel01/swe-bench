from decimal import Decimal

from money import allocate, round_money


def test_bankers_rounding_half_to_even():
    assert round_money(Decimal("0.005")) == Decimal("0.00")
    assert round_money(Decimal("0.025")) == Decimal("0.02")
    assert round_money(Decimal("0.045")) == Decimal("0.04")
    assert round_money(Decimal("0.125")) == Decimal("0.12")
    assert round_money(Decimal("0.145")) == Decimal("0.14")


def test_rounding_non_half_cases():
    assert round_money(Decimal("0.126")) == Decimal("0.13")
    assert round_money(Decimal("0.124")) == Decimal("0.12")


def test_rounding_places_arg():
    assert round_money(Decimal("1.2345"), 3) == Decimal("1.234")


def test_allocate_sums_exactly():
    parts = allocate(Decimal("1.00"), [1, 1, 1])
    assert sum(parts) == Decimal("1.00")
    assert sorted(parts) == [Decimal("0.33"), Decimal("0.33"), Decimal("0.34")]


def test_allocate_proportional():
    parts = allocate(Decimal("10.00"), [1, 2, 3])
    assert sum(parts) == Decimal("10.00")
    assert parts == [Decimal("1.67"), Decimal("3.33"), Decimal("5.00")]


def test_allocate_validation():
    import pytest
    with pytest.raises(ValueError):
        allocate(Decimal("1.00"), [])
    with pytest.raises(ValueError):
        allocate(Decimal("1.00"), [0, 0])
    with pytest.raises(ValueError):
        allocate(Decimal("1.00"), [-1, 2])
