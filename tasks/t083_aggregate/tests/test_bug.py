from groupby import aggregate


def test_composite_key_does_not_collide():
    rows = [
        {"g": "a", "s": "12", "v": 10},
        {"g": "a1", "s": "2", "v": 20},
    ]
    result = aggregate(rows)
    assert len(result) == 2


def test_mean_keeps_fraction():
    rows = [{"g": "z", "s": "z", "v": 1}, {"g": "z", "s": "z", "v": 2}]
    result = aggregate(rows)
    assert list(result.values())[0] == 1.5
