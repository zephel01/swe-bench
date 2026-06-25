from lru import LRUCache


def test_capacity_never_exceeded():
    c = LRUCache(3)
    for i in range(10):
        c.put(i, i)
        assert len(c) <= 3
    assert len(c) == 3


def test_oldest_evicted_first():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)
    assert len(c) == 2
    assert c.get("a") is None
