from geo import distance


def test_identical_points():
    assert distance(52.0, 4.0, 52.0, 4.0) == 0.0


def test_long_distance():
    d = distance(36.12, -86.67, 33.94, -118.40)
    assert abs(d - 2886.45) < 1.0


def test_symmetry():
    d1 = distance(10.0, 20.0, 30.0, 40.0)
    d2 = distance(30.0, 40.0, 10.0, 20.0)
    assert abs(d1 - d2) < 1e-9
