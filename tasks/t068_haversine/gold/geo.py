import math

EARTH_RADIUS_KM = 6371.0088


def distance(lat1, lon1, lat2, lon2):
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    hav_lat = math.sin(dphi / 2.0) ** 2
    hav_lon = math.sin(dlon / 2.0) ** 2
    a = hav_lat + math.cos(p1) * math.cos(p2) * hav_lon
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))
