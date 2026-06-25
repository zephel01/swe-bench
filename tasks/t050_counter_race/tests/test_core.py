from counter import Counter


def test_single_thread():
    c = Counter()
    for _ in range(1000):
        c.increment()
    c.add(5)
    assert c.value == 1005


def test_get_and_reset_single_thread():
    c = Counter()
    c.add(7)
    assert c.get_and_reset() == 7
    assert c.value == 0
