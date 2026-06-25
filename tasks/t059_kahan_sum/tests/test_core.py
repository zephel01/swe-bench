from fsum import total


def test_small_exact():
    assert total([1.0, 2.0, 3.0]) == 6.0


def test_empty():
    assert total([]) == 0.0
