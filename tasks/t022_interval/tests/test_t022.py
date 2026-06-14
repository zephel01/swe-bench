import pytest

from intervals import IntervalSet


def test_adjacent_integers_merge():
    s = IntervalSet()
    s.add(1, 2)
    s.add(3, 4)
    assert s.intervals() == [(1, 4)]


def test_overlap_merge():
    s = IntervalSet()
    s.add(1, 5)
    s.add(3, 8)
    assert s.intervals() == [(1, 8)]


def test_gap_kept_separate():
    s = IntervalSet()
    s.add(1, 2)
    s.add(5, 6)
    assert s.intervals() == [(1, 2), (5, 6)]


def test_total_length_and_contains():
    s = IntervalSet()
    s.add(1, 2)
    s.add(3, 4)
    assert s.total_length() == 4
    assert s.contains(2) and s.contains(3)
    assert not s.contains(0)


def test_remove_splits():
    s = IntervalSet()
    s.add(1, 10)
    s.remove(4, 6)
    assert s.intervals() == [(1, 3), (7, 10)]


def test_validation():
    s = IntervalSet()
    with pytest.raises(ValueError):
        s.add(5, 1)
