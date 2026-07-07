import math

from geo import EARTH_RADIUS_KM, distance


def test_tiny_meridian_step():
    lat, lon = 45.0, 10.0
    true = EARTH_RADIUS_KM * math.radians(1e-7)
    d = distance(lat, lon, lat + 1e-7, lon)
    assert abs(d - true) / true < 1e-3


def test_small_meridian_step():
    lat, lon = 45.0, 10.0
    true = EARTH_RADIUS_KM * math.radians(1e-6)
    d = distance(lat, lon, lat + 1e-6, lon)
    assert abs(d - true) / true < 1e-3
