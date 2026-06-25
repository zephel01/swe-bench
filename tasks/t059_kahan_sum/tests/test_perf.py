import time

from fsum import total


def test_large_sum_completes():
    values = [0.1] * 1_000_000
    start = time.perf_counter()
    result = total(values)
    assert time.perf_counter() - start < 5.0
    assert abs(result - 100000.0) < 1e-3
