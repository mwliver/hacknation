from mcod.aed.geo import close_pairs, haversine_m


def test_haversine_known_distance():
    # Warszawa – Kraków, about 252 km
    assert 250_000 < haversine_m(52.2297, 21.0122, 50.0647, 19.9450) < 254_000
    assert haversine_m(52.0, 21.0, 52.0, 21.0) == 0


def test_close_pairs():
    points = [(52.1050, 21.2600), (52.10502, 21.26002), (52.1060, 21.2600), (50.0647, 19.9450)]
    pairs = list(close_pairs(points, 5.0))
    assert [(i, j) for i, j, _ in pairs] == [(0, 1)]
    assert 2 < pairs[0][2] < 3.5
    assert {(i, j) for i, j, _ in close_pairs(points, 120.0)} == {(0, 1), (0, 2), (1, 2)}


def test_close_pairs_across_grid_cells():
    # points on both sides of a cell border must still be found
    points = [(52.0, 20.99999), (52.0, 21.00001)]
    assert [(i, j) for i, j, _ in close_pairs(points, 5.0)] == [(0, 1)]
