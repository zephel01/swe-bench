from dedup import dedup


def test_first_occurrence_kept():
    assert dedup([1, 2, 1, 3, 2, 4]) == [1, 2, 3, 4]


def test_unhashable_elements_dedup_by_equality():
    a = {"x": 1}
    c = [1, 2]
    assert dedup([a, {"x": 1}, c, [1, 2], a]) == [{"x": 1}, [1, 2]]


def test_mixed_hashable_and_unhashable():
    assert dedup([1, [0], 1, "a", [0], "a"]) == [1, [0], "a"]
