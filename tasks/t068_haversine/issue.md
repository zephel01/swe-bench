# Bug: great-circle distance collapses to zero for nearby points

`distance(lat1, lon1, lat2, lon2)` returns the great-circle distance in
kilometers between two points on the Earth (radius `EARTH_RADIUS_KM`). It is
accurate for far-apart cities but loses all precision for points that are close
together.

Failing example:

    lat, lon = 45.0, 10.0
    distance(lat, lon, lat + 1e-7, lon)
    # returns 0.0, expected about 1.11e-5 km (roughly 1.1 cm)

The two points differ by 1e-7 degrees of latitude on the same meridian, so the
distance is exactly `EARTH_RADIUS_KM * radians(1e-7)`, about `1.11e-5` km. The
function returns `0.0` instead. Long distances such as Nashville to Los Angeles
(about `2886` km) are computed correctly.
