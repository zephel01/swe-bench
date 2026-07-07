import math

from logsumexp import log_sum_exp


def test_pair_of_zeros():
    assert abs(log_sum_exp([0.0, 0.0]) - math.log(2.0)) < 1e-12


def test_small_values():
    xs = [1.0, 2.0, 3.0]
    expected = math.log(sum(math.exp(x) for x in xs))
    assert abs(log_sum_exp(xs) - expected) < 1e-12


def test_single_small():
    assert abs(log_sum_exp([2.5]) - 2.5) < 1e-12
