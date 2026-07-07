from geomean import geometric_mean


def test_simple():
    assert abs(geometric_mean([1.0, 2.0, 4.0]) - 2.0) < 1e-12


def test_pair():
    assert abs(geometric_mean([4.0, 9.0]) - 6.0) < 1e-12


def test_all_equal():
    assert abs(geometric_mean([2.0] * 1000) - 2.0) < 1e-9
