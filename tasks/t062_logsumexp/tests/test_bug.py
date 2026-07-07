import math

from logsumexp import log_sum_exp


def test_large_positive():
    assert abs(log_sum_exp([1000.0, 1000.0]) - (1000.0 + math.log(2.0))) < 1e-9


def test_large_negative():
    assert abs(log_sum_exp([-1000.0, -1000.0]) - (-1000.0 + math.log(2.0))) < 1e-9


def test_single_large():
    assert abs(log_sum_exp([710.0]) - 710.0) < 1e-9
