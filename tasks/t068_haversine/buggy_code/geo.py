import math

EARTH_RADIUS_KM = 6371.0088


def distance(lat1, lon1, lat2, lon2):
    p1 = math.radians(lat1)
    p2 = math.radians(lat2)
    dlon = math.radians(lon2 - lon1)
    cos_c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dlon)
    return EARTH_RADIUS_KM * math.acos(cos_c)
