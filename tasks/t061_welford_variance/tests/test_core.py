from spread import variance


def test_small_data():
    assert abs(variance([1.0, 2.0, 3.0, 4.0, 5.0]) - 2.5) < 1e-9


def test_moderate_offset_ok():
    vals = [x + 1e3 for x in [1.0, 2.0, 3.0, 4.0, 5.0]]
    assert abs(variance(vals) - 2.5) < 1e-9


def test_degenerate():
    assert variance([]) == 0.0
    assert variance([42.0]) == 0.0
