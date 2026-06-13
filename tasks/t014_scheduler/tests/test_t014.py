import pytest

from scheduler import Scheduler


def test_priority_order():
    s = Scheduler()
    s.add_job("low", 1)
    s.add_job("high", 10)
    s.add_job("mid", 5)
    assert s.run_order() == ["high", "mid", "low"]


def test_fifo_on_ties():
    s = Scheduler()
    s.add_job("first", 5)
    s.add_job("second", 5)
    s.add_job("third", 5)
    assert s.run_order() == ["first", "second", "third"]


def test_mixed():
    s = Scheduler()
    s.add_job("a", 1)
    s.add_job("b", 3)
    s.add_job("c", 3)
    s.add_job("d", 2)
    assert s.run_order() == ["b", "c", "d", "a"]


def test_empty_pop():
    from pq import PriorityQueue
    with pytest.raises(IndexError):
        PriorityQueue().pop()
