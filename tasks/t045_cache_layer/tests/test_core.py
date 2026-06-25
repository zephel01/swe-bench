from cache import TTLCache


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_put_get_before_expiry():
    c = Clock()
    cache = TTLCache(clock=c)
    cache.put("k", {"x": 1}, 10)
    c.t = 5
    assert cache.get("k") == {"x": 1}


def test_missing_key():
    assert TTLCache().get("nope") is None
