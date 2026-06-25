import time

from dedup import dedup


def test_large_input_is_fast():
    data = list(range(40_000)) * 2
    start = time.perf_counter()
    out = dedup(data)
    elapsed = time.perf_counter() - start
    assert out == list(range(40_000))
    assert elapsed < 1.0
