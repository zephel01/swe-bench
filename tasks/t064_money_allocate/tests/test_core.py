from allocate import allocate


def test_even_split():
    assert allocate(90, [1, 1, 1]) == [30, 30, 30]


def test_weighted_exact():
    assert allocate(100, [1, 3]) == [25, 75]


def test_single_part():
    assert allocate(100, [1]) == [100]
