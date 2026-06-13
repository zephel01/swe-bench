from stats import average


def test_empty():
    assert average([]) == 0.0


def test_basic():
    assert average([1, 2, 3]) == 2.0


def test_floats():
    assert abs(average([1.5, 2.5]) - 2.0) < 1e-9
