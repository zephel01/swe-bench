from counter import Counter


def test_single_thread():
    c = Counter()
    for _ in range(1000):
        c.increment()
    assert c.value == 1000
