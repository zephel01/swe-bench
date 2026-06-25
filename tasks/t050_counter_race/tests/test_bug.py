from concurrent.futures import ThreadPoolExecutor

from counter import Counter


def test_concurrent_total_exact():
    c = Counter()

    def work():
        for _ in range(1000):
            c.increment()

    with ThreadPoolExecutor(max_workers=8) as ex:
        futures = [ex.submit(work) for _ in range(8)]
        for f in futures:
            f.result()
    assert c.value == 8000
