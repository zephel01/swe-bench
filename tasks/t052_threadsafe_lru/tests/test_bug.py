import threading

from lru import LRUCache


def test_get_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    assert c.get("a") == 1     # "a" becomes most-recently-used
    c.put("c", 3)              # must evict "b" (least recent), not "a"
    assert c.get("b") is None
    assert c.get("a") == 1
    assert c.get("c") == 3


def test_update_existing_refreshes_recency():
    c = LRUCache(2)
    c.put("a", 1)
    c.put("b", 2)
    c.put("a", 10)             # update "a" -> most recent
    c.put("c", 3)              # evict "b"
    assert c.get("b") is None
    assert c.get("a") == 10
    assert len(c) == 2


def test_concurrent_access_stays_bounded():
    c = LRUCache(50)

    def work(base):
        for i in range(2000):
            c.put((base, i % 100), i)
            c.get((base, i % 100))

    threads = [threading.Thread(target=work, args=(t,)) for t in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(c) <= 50
