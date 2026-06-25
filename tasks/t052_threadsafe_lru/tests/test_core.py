from lru import LRUCache


def test_basic_get_put():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1
    assert c.get("b") == 2


def test_capacity_enforced():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("c", 3)          # no gets: oldest "a" is evicted
    assert len(c) == 2
    assert c.get("a") is None
    assert c.get("c") == 3


def test_validation():
    import pytest
    with pytest.raises(ValueError):
        LRUCache(0)
