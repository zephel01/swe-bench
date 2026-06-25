from dedup import dedup


def test_order_preserved():
    assert dedup([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_empty():
    assert dedup([]) == []
