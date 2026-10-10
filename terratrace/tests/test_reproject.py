"""Reprojection pure-helper fixtures (no rasterio needed)."""
from terratrace import reproject as rp


def test_geographic_crs():
    assert rp.geographic_crs("earth") == "EPSG:4326"
    mars = rp.geographic_crs("mars")
    assert "3396190" in mars and "longlat" in mars


def test_local_aeqd_strings():
    e = rp.local_aeqd(36.2, -115.6, "earth")
    assert "aeqd" in e and "lat_0=36.2" in e and "WGS84" in e
    m = rp.local_aeqd(0.0, 125.0, "mars")
    assert "aeqd" in m and "3396190" in m and "WGS84" not in m


def test_centroid():
    lon0, lat0 = rp.centroid((-116.0, 36.0, -115.0, 37.0))
    assert abs(lon0 + 115.5) < 1e-9
    assert abs(lat0 - 36.5) < 1e-9


def test_grid_size():
    # 10 km x 5 km at 1 km -> 10 x 5
    w, h = rp.grid_size(0.0, 0.0, 10000.0, 5000.0, 1000.0)
    assert (w, h) == (10, 5)


def test_grid_size_rejects_bad_resolution():
    try:
        rp.grid_size(0, 0, 10, 10, 0)
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_unknown_body_raises():
    for fn in (lambda: rp.geographic_crs("venus"), lambda: rp.local_aeqd(0, 0, "venus")):
        try:
            fn()
            raised = False
        except ValueError:
            raised = True
        assert raised


def test_moon_is_supported_body():
    # Moon (LRO/LOLA sphere) is a first-class body alongside Mars and Earth.
    g = rp.geographic_crs("moon")
    assert "1737400" in g and "longlat" in g
    a = rp.local_aeqd(10.0, 20.0, "moon")
    assert "aeqd" in a and "1737400" in a and "WGS84" not in a
    assert rp.body_radius_m("moon") == 1737400.0
    # Mars strings are byte-identical to before Moon was added (no regression).
    assert rp.geographic_crs("mars") == "+proj=longlat +a=3396190.0 +b=3396190.0 +no_defs"


def test_mercury_and_ceres_are_supported_bodies():
    # Multi-body: Mercury (MESSENGER) and Ceres (Dawn) spheres are first-class too.
    assert "2439400" in rp.geographic_crs("mercury")
    assert "469730" in rp.geographic_crs("ceres")
    assert rp.body_radius_m("mercury") == 2439400.0 and rp.body_radius_m("ceres") == 469730.0
    for b in ("mercury", "ceres"):
        a = rp.local_aeqd(0.0, 0.0, b)
        assert "aeqd" in a and "WGS84" not in a
