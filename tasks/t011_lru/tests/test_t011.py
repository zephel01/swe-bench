import pytest

from lru import LRUCache


def test_eviction_order():
    cache = LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    assert cache.get(1) == "a"      # 1 is now most recently used
    cache.put(3, "c")               # should evict 2
    assert 3 in cache
    assert 1 in cache
    assert 2 not in cache


def test_update_refreshes():
    cache = LRUCache(2)
    cache.put(1, "a")
    cache.put(2, "b")
    cache.put(1, "a2")              # refresh 1
    cache.put(3, "c")               # should evict 2
    assert cache.get(1) == "a2"
    assert cache.get(2) is None
    assert cache.get(3) == "c"


def test_capacity():
    cache = LRUCache(3)
    for i in range(10):
        cache.put(i, i)
    assert len(cache) == 3


def test_invalid_capacity():
    with pytest.raises(ValueError):
        LRUCache(0)
