import math


def haversine_m(lat1, lng1, lat2, lng2) -> int:
    """Great-circle distance in meters."""
    lat1, lng1, lat2, lng2 = (float(v) for v in (lat1, lng1, lat2, lng2))
    r = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return round(2 * r * math.asin(math.sqrt(a)))
