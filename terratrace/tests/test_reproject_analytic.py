"""The reprojection, validated against closed-form geodesy rather than a second GDAL wrapper.

`docs/INDEPENDENT-GIS-REPRODUCTION.md` carried an honest gap for a while: the "independent"
reproduction of the reprojection compared `rasterio.warp` with `gdalwarp`, and both are GDAL. Two
wrappers around one library is one implementation. The replacement compares the projection against
mathematics, using the defining property of azimuthal equidistant: the distance from the projection
centre to any projected point IS the geodesic distance on the body.

The pure-arithmetic references are tested here unconditionally (they need nothing but `math`), so a
mistake in the reference is caught on the NumPy-only CI interpreters. The comparison against the
actual projection needs rasterio and is therefore gated.

House style: module-level ``def test_*()`` functions, no pytest, no optional imports at module scope.
"""
import importlib.util
import math
import pathlib

_ROOT = pathlib.Path(__file__).resolve().parent.parent


def _load():
    spec = importlib.util.spec_from_file_location(
        "reproject_analytic_check", _ROOT / "scripts" / "reproject_analytic_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_great_circle_reference_matches_closed_form():
    """On a sphere the reference is exact, so it must reproduce hand-checkable values."""
    m = _load()
    R = 1737400.0
    # one degree along the equator and along a meridian are both R * 1 degree
    for lat1, lon1, lat2, lon2 in [(0.0, 0.0, 0.0, 1.0), (0.0, 0.0, 1.0, 0.0), (-10.0, 5.0, -9.0, 5.0)]:
        got = m.great_circle_m(R, lat1, lon1, lat2, lon2)
        want = R * math.radians(1.0)
        assert abs(got - want) < 1e-6, f"{got} != {want}"
    # antipodes are exactly half a circumference
    assert abs(m.great_circle_m(R, 0.0, 0.0, 0.0, 180.0) - math.pi * R) < 1e-6
    # and the same point is zero distance
    assert m.great_circle_m(R, 12.0, 34.0, 12.0, 34.0) == 0.0


def test_meridional_reference_reduces_to_the_sphere_case():
    """Flattening zero must reproduce the spherical arc, or the quadrature is wrong."""
    m = _load()
    a = 6378137.0
    for span in (0.01, 0.1, 1.0):
        got = m.meridional_arc_m(a, 0.0, 10.0, 10.0 + span)
        want = a * math.radians(span)
        assert abs(got - want) < 1e-6, f"f=0 span {span}: {got} != {want}"


def test_meridional_reference_is_shorter_than_the_spherical_arc_on_an_ellipsoid():
    """The known sign: an ellipsoid's meridional arc is SHORTER than a sphere of semi-major radius.

    This is the check that caught the real defect. An earlier revision used a half-remembered
    geodesic formula that produced a *longer* arc, and reported the projection as being 107 m wrong
    when the projection was right. Getting the sign right is the whole content of the check.
    """
    m = _load()
    a, f = 6378137.0, 1.0 / 298.257223563
    sphere = a * math.radians(1.0)
    ellipsoid = m.meridional_arc_m(a, f, 36.2, 37.2)
    assert ellipsoid < sphere, f"ellipsoidal arc {ellipsoid} should be shorter than {sphere}"
    # and the reduction is of order the flattening, not of order one
    assert 0.001 < (sphere - ellipsoid) / sphere < 0.01, "reduction is not the right magnitude"


def test_equatorial_reference_is_exactly_a_times_delta_lambda():
    """On the equator the geodesic is a circular arc of radius a — no quadrature needed."""
    m = _load()
    a = 6378137.0
    assert abs(m.equatorial_arc_m(a, 0.0, 1.0) - a * math.radians(1.0)) < 1e-9
    assert abs(m.equatorial_arc_m(a, 10.0, 10.5) - a * math.radians(0.5)) < 1e-9
    assert m.equatorial_arc_m(a, 5.0, 4.0) == m.equatorial_arc_m(a, 4.0, 5.0)   # symmetric


def test_the_projection_agrees_with_the_closed_form_references():
    """The end-to-end check: projected distances-from-centre vs the references above.

    Gated on rasterio (the projection is exercised through the same GDAL path the engine uses).
    """
    try:
        import rasterio                                   # noqa: F401
        from rasterio.warp import transform as _t         # noqa: F401
    except Exception:
        return
    m = _load()
    rc = m.main([])
    assert rc == 0, "the reprojection no longer matches closed-form geodesy"


def test_the_check_can_actually_fail():
    """A reference that always agrees proves nothing, so a wrong radius must be rejected.

    Scaling the Moon's radius by 1% is a realistic failure (the engine's lunar constant is a literal
    in one place), and the spherical reference must then disagree by ~1%.
    """
    m = _load()
    R = 1737400.0
    correct = m.great_circle_m(R, 89.0, 0.0, 89.0, 0.5)
    wrong = m.great_circle_m(R * 1.01, 89.0, 0.0, 89.0, 0.5)
    assert abs(wrong - correct) / correct > 0.009, "a 1% radius error must move the reference by ~1%"
