from dedup import dedup


def test_order_preserved():
    assert dedup([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_small_unhashable():
    assert dedup([{"x": 1}, {"x": 1}, [0]]) == [{"x": 1}, [0]]
