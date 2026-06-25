from cache import TTLCache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_exactly_at_expiry_is_miss():
    c = Clock()
    cache = TTLCache(clock=c)
    cache.put("k", "v", 10)
    c.t = 10
    assert cache.get("k") is None


def test_expired_entry_evicted():
    c = Clock()
    cache = TTLCache(clock=c)
    cache.put("k", "v", 10)
    c.t = 11
    cache.get("k")
    assert len(cache.backend) == 0
