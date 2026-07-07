from envelope import Event
from processor import Processor


def test_in_order_apply():
    p = Processor()
    p.submit(Event(1, "k1", 10))
    p.submit(Event(2, "k2", 20))
    p.submit(Event(3, "k3", 30))
    assert p.applied == [1, 2, 3]
    assert p.total == 60
    assert p.next_seq == 4


def test_duplicate_key_ignored():
    p = Processor()
    p.submit(Event(1, "k1", 10))
    p.submit(Event(1, "k1", 10))     # redelivery of the same event
    p.submit(Event(2, "k2", 5))
    assert p.applied == [1, 2]
    assert p.total == 15
