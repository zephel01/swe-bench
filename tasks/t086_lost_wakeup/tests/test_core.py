import threading

from buffer import BoundedBuffer


def test_single_producer_single_consumer_fifo():
    buf = BoundedBuffer(4)
    for i in range(4):
        buf.put(i)
    assert [buf.get() for _ in range(4)] == [0, 1, 2, 3]


def test_blocking_get_then_put():
    buf = BoundedBuffer(1)
    got = []

    def consume():
        got.append(buf.get())

    t = threading.Thread(target=consume)
    t.start()
    buf.put(99)
    t.join(timeout=3.0)
    assert not t.is_alive()
    assert got == [99]


def test_matched_producer_consumer_counts():
    buf = BoundedBuffer(2)
    total = 200
    received = []

    def consumer():
        for _ in range(total):
            received.append(buf.get())

    t = threading.Thread(target=consumer)
    t.start()
    for i in range(total):
        buf.put(i)
    t.join(timeout=5.0)
    assert not t.is_alive()
    assert received == list(range(total))
