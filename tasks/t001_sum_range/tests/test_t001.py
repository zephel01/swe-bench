from sum_range import sum_to_n


def test_basic():
    assert sum_to_n(10) == 55


def test_one():
    assert sum_to_n(1) == 1


def test_zero():
    assert sum_to_n(0) == 0


def test_large():
    assert sum_to_n(100) == 5050
