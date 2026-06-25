from dedup import dedup


def test_order_preserved():
    assert dedup([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_empty():
    assert dedup([]) == []


def test_no_duplicates():
    assert dedup(["a", "b", "c"]) == ["a", "b", "c"]
