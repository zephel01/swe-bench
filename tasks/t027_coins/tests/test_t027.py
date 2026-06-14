import pytest

from coins import min_coins


def test_non_canonical_needs_dp():
    assert min_coins([1, 3, 4], 6) == 2      # 3+3 (貪欲は 4+1+1=3)


def test_canonical_system():
    assert min_coins([1, 2, 5], 11) == 3      # 5+5+1


def test_impossible():
    assert min_coins([2], 3) == -1
    assert min_coins([5, 10], 3) == -1


def test_zero_amount():
    assert min_coins([1, 2, 5], 0) == 0
    assert min_coins([], 0) == 0


def test_validation():
    with pytest.raises(ValueError):
        min_coins([1], -1)
