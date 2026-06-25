from dedup import dedup


def test_first_occurrence_kept():
    assert dedup([1, 2, 1, 3, 2, 4]) == [1, 2, 3, 4]
