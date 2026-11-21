"""Small geodesic helpers (no external dependencies)."""

import math
from collections import defaultdict
from typing import Dict, Iterable, Iterator, List, Sequence, Tuple

EARTH_RADIUS_M = 6_371_008.8
METERS_PER_DEGREE_LAT = 111_320.0
# Northernmost latitude of Poland – used to size grid cells so that they are never too small in longitude.
_MAX_LAT_FOR_GRID = 55.0

Point = Tuple[float, float]  # (lat, lon)


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = phi2 - phi1
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def _cell_size(radius_m: float) -> Tuple[float, float]:
    lat_size = radius_m / METERS_PER_DEGREE_LAT
    lon_size = radius_m / (METERS_PER_DEGREE_LAT * math.cos(math.radians(_MAX_LAT_FOR_GRID)))
    return lat_size, lon_size


def close_pairs(points: Sequence[Point], radius_m: float) -> Iterator[Tuple[int, int, float]]:
    """
    Yields ``(i, j, distance_m)`` for every pair of points (i < j) closer than ``radius_m``.
    Uses a uniform grid, so it is roughly linear for evenly distributed points.
    """
    lat_size, lon_size = _cell_size(radius_m)
    grid: Dict[Tuple[int, int], List[int]] = defaultdict(list)
    for idx, (lat, lon) in enumerate(points):
        grid[(int(math.floor(lat / lat_size)), int(math.floor(lon / lon_size)))].append(idx)
    for (cell_lat, cell_lon), members in grid.items():
        neighbours: Iterable[int] = (
            other for d_lat in (-1, 0, 1) for d_lon in (-1, 0, 1) for other in grid.get((cell_lat + d_lat, cell_lon + d_lon), ())
        )
        candidates = list(neighbours)
        for i in members:
            for j in candidates:
                if j <= i:
                    continue
                distance = haversine_m(points[i][0], points[i][1], points[j][0], points[j][1])
                if distance < radius_m:
                    yield i, j, distance
