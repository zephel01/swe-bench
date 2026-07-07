from envelope import Event
from processor import Processor


def test_gap_is_not_skipped():
    p = Processor()
    p.submit(Event(1, "k1", 10))
    p.submit(Event(3, "k3", 30))   # arrives before 2 -> must wait for the gap
    assert p.applied == [1]        # 3 is buffered, not applied yet
    assert p.next_seq == 2

    p.submit(Event(2, "k2", 20))   # fills the gap; now 2 then 3 may apply
    assert p.applied == [1, 2, 3]
    assert p.total == 60
    assert p.next_seq == 4


def test_late_event_after_premature_skip_not_lost():
    p = Processor()
    p.submit(Event(1, "k1", 1))
    p.submit(Event(4, "k4", 4))    # big gap
    p.submit(Event(3, "k3", 3))    # still a gap at 2
    assert p.applied == [1]
    p.submit(Event(2, "k2", 2))    # fills the gap: 2,3,4 flush in order
    assert p.applied == [1, 2, 3, 4]
    assert p.total == 10
