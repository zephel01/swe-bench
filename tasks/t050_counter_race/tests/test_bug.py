import threading
from concurrent.futures import ThreadPoolExecutor

from counter import Counter


def test_concurrent_total_exact():
    c = Counter()

    def work():
        for _ in range(1000):
            c.increment()

    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in [ex.submit(work) for _ in range(8)]:
            f.result()
    assert c.value == 8000


def test_increment_with_concurrent_reset_preserves_total():
    c = Counter()
    collected = []
    stop = threading.Event()

    def worker():
        for _ in range(1000):
            c.increment()

    def reaper():
        while not stop.is_set():
            collected.append(c.get_and_reset())

    rt = threading.Thread(target=reaper)
    rt.start()
    workers = [threading.Thread(target=worker) for _ in range(8)]
    for t in workers:
        t.start()
    for t in workers:
        t.join()
    stop.set()
    rt.join()
    collected.append(c.get_and_reset())
    assert sum(collected) == 8000
