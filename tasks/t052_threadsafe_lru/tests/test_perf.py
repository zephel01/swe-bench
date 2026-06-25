import threading

from lru import LRUCache


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
