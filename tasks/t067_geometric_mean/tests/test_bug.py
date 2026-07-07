from geomean import geometric_mean


def test_large_magnitude():
    result = geometric_mean([1e200] * 5)
    assert abs(result - 1e200) / 1e200 < 1e-9


def test_small_magnitude():
    result = geometric_mean([1e-200] * 5)
    assert abs(result - 1e-200) / 1e-200 < 1e-9


def test_mixed_extreme():
    result = geometric_mean([1e200, 1e200, 1e-200, 1e-200])
    assert abs(result - 1.0) < 1e-6
