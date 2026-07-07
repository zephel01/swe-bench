from groupby import aggregate


def test_two_distinct_groups_integer_means():
    rows = [
        {"g": "a", "s": "1", "v": 2},
        {"g": "a", "s": "1", "v": 4},
        {"g": "b", "s": "2", "v": 10},
    ]
    result = aggregate(rows)
    assert len(result) == 2
    assert set(result.values()) == {3.0, 10.0}


def test_single_group_integer_mean():
    rows = [{"g": "x", "s": "y", "v": 4}, {"g": "x", "s": "y", "v": 6}]
    assert list(aggregate(rows).values()) == [5.0]
