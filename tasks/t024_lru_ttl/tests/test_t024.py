import pytest

from cache import LRUTTLCache


def make(cap, ttl):
    t = {"now": 0}
    c = LRUTTLCache(cap, ttl, lambda: t["now"])
    return c, t


def test_expires_at_boundary():
    c, t = make(2, 10)
    c.put("a", "A")
    t["now"] = 5
    assert c.get("a") == "A"
    t["now"] = 10            # ちょうど期限 → 失効
    assert c.get("a") is None


def test_lru_eviction_among_live():
    c, t = make(2, 100)
    c.put("a", "A")
    t["now"] = 1
    c.put("b", "B")
    t["now"] = 2
    assert c.get("a") == "A"   # a を最近使用に
    t["now"] = 3
    c.put("c", "C")           # b (LRU) が落ちる
    assert c.get("b") is None
    assert c.get("a") == "A"
    assert c.get("c") == "C"


def test_expired_frees_capacity():
    c, t = make(1, 5)
    c.put("a", "A")
    t["now"] = 6
    c.put("b", "B")
    assert c.get("a") is None
    assert c.get("b") == "B"


def test_validation():
    with pytest.raises(ValueError):
        LRUTTLCache(0, 10, lambda: 0)
    with pytest.raises(ValueError):
        LRUTTLCache(2, 0, lambda: 0)
