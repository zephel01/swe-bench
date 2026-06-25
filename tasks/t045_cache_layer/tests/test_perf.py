import time

from cache import TTLCache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_get_is_constant_time_under_load():
    c = Clock()
    cache = TTLCache(clock=c)
    for i in range(50_000):
        cache.put(str(i), i, 1000)
    start = time.perf_counter()
    for i in range(50_000):
        assert cache.get(str(i)) == i
    assert time.perf_counter() - start < 3.0
