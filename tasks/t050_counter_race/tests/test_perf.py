import time
from concurrent.futures import ThreadPoolExecutor

from counter import Counter


def test_completes_under_contention():
    c = Counter()

    def work():
        for _ in range(2000):
            c.increment()

    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=8) as ex:
        for f in [ex.submit(work) for _ in range(8)]:
            f.result()
    assert time.perf_counter() - start < 10.0
    assert c.value == 16000
