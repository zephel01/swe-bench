from lru import LRUCache


def test_basic_get_put():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


def test_lru_eviction_order():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.get("a")          # a is now most-recent
    c.put("c", 3)       # evicts b (least-recent)
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3
