"""Five-body geometry, validated ANALYTICALLY -- and labelled as such.

WHAT THIS FILE IS, AND WHAT IT IS NOT
-------------------------------------
It validates the *projection and grid arithmetic* for all five bodies: Earth, Mars, the Moon,
Mercury and Ceres. It does NOT validate any terrain comparison on Mars, Mercury or Ceres, because
there is no real DEM of Mercury or Ceres in this repository and the Mars comparison is validated
elsewhere on its own data. The distinction is the whole point of the file and it is written down in
code rather than in prose:

    ANALYTIC_BODIES  = all five   -- projection geometry, grid arithmetic, footprint equality
    REAL_DATA_BODIES = earth, moon -- an actual DEM was read and compared

Claiming five-body reprojection validation from a real run on two bodies would be exactly the kind
of overreach this project keeps withdrawing, so the two lists are declared here and a test asserts
they partition the five bodies rather than one quietly growing into the other.

THE INVARIANT BEING TESTED
--------------------------
Azimuthal equidistant's defining property: the distance from the projection centre to any projected
point IS the geodesic distance on the body. Everything the comparison layer claims follows from it --
"a 500 m cell is 500 m of ground" is not a convention, it is this property.

It is checked against TWO independent closed-form geodesy implementations written here, not against
another PROJ call:

  * a great-circle distance on a sphere of the body's own radius -- exact for the four spherical
    bodies, which is how Mars, the Moon, Mercury and Ceres are all defined in `reproject`;
  * Vincenty's inverse formula on the WGS84 ellipsoid for Earth, because Earth is the one
    ellipsoidal body and a spherical yardstick is the wrong instrument for it.

That second point is not pedantry, it is a mistake this file already made once. The first version
measured Earth against a sphere and reported the projection as 18.9 m off over 9 km -- 0.21 %, which
would have been a real defect if true. It was not: it was the *yardstick* that was wrong. Against a
proper ellipsoidal geodesic the same projection is exact to 1.4e-7 m. A check is only as good as
the thing it measures against, and a wrong reference silently becomes a fabricated defect.
"""
import math
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from harness import require                                        # noqa: E402
from terratrace import common_grid as cg, reproject                # noqa: E402

ANALYTIC_BODIES = ("earth", "mars", "moon", "mercury", "ceres")
REAL_DATA_BODIES = ("earth", "moon")
SYNTHETIC_ONLY_BODIES = ("mars", "mercury", "ceres")

# One site per body, at the latitude the body is actually used at where there is one. The lunar
# entry is the real Connecting-ridge centre; Mercury and Ceres have no real data here, so their
# sites are arbitrary but include a high-latitude one, where a projection is most likely to break.
SITE = {"earth": (36.2, -115.6), "mars": (-4.5, 135.0), "moon": (-89.46316, -137.48955),
        "mercury": (60.0, -150.0), "ceres": (40.0, 200.0)}

# The footprints the project actually compares at, in metres.
PROJECT_FOOTPRINTS = ((500.0, 18), (750.0, 12), (1000.0, 9),          # the lunar/Earth panel
                      (1500.0, 40), (2000.0, 30), (3000.0, 20))      # the Mars panel

# The tolerance is ANGULAR, because the only error present is floating-point noise in PROJ's own
# arithmetic and that noise maps to metres in proportion to the body's radius. A fixed metric
# tolerance would be either meaningless on Ceres (R = 470 km) or absurdly loose on Earth.
# Measured worst case over every body and every offset tested: 1.4e-7 m on Earth at 9 km, i.e.
# 1.6e-11 rad; Ceres at the projection centre is the loosest at 0.007 m, i.e. 1.5e-8 rad.
ANGULAR_TOL = 3e-8            # radians
ORIGIN_TOL_M = 0.02           # the projection centre must map to itself to well under a centimetre


def _transform(src, dst, xs, ys):
    """PROJ, through rasterio's own API -- never a direct pyproj import.

    `pyproj` is a transitive dependency of rasterio and is declared nowhere; a direct import is
    invisible locally and fatal on the NumPy-only CI interpreter. That trap has bitten this project
    three times and one of those was a red CI run, so this file goes through rasterio.
    """
    require(_have_rasterio(), "rasterio is not installed, so PROJ cannot be called from here")
    from rasterio.warp import transform as _t
    return _t(src, dst, xs, ys)


def _have_rasterio():
    try:
        import rasterio  # noqa: F401
        return True
    except Exception:
        return False


def great_circle_m(lat1, lon1, lat2, lon2, radius_m):
    """Spherical geodesic (law of cosines). The exact instrument for a spherical body."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = (math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl))
    return radius_m * math.acos(max(-1.0, min(1.0, c)))


def vincenty_m(lat1, lon1, lat2, lon2, a=6378137.0, f=1.0 / 298.257223563):
    """Vincenty's inverse formula on the WGS84 ellipsoid. The exact instrument for EARTH.

    Written out here rather than imported, so the check is independent of the library under test.
    Converges to ~1e-13 rad in this range; returns the geodesic length in metres.
    """
    b = a * (1 - f)
    L = math.radians(lon2 - lon1)
    U1 = math.atan((1 - f) * math.tan(math.radians(lat1)))
    U2 = math.atan((1 - f) * math.tan(math.radians(lat2)))
    sU1, cU1, sU2, cU2 = math.sin(U1), math.cos(U1), math.sin(U2), math.cos(U2)
    lam = L
    for _ in range(200):
        sl, cl = math.sin(lam), math.cos(lam)
        ss = math.sqrt((cU2 * sl) ** 2 + (cU1 * sU2 - sU1 * cU2 * cl) ** 2)
        if ss == 0:
            return 0.0
        cs = sU1 * sU2 + cU1 * cU2 * cl
        sigma = math.atan2(ss, cs)
        sa = cU1 * cU2 * sl / ss
        c2a = 1 - sa * sa
        c2sm = (cs - 2 * sU1 * sU2 / c2a) if c2a != 0 else 0.0
        C = f / 16 * c2a * (4 + f * (4 - 3 * c2a))
        lam_prev = lam
        lam = L + (1 - C) * f * sa * (sigma + C * ss * (c2sm + C * cs * (-1 + 2 * c2sm ** 2)))
        if abs(lam - lam_prev) < 1e-13:
            break
    u2 = c2a * (a * a - b * b) / (b * b)
    A = 1 + u2 / 16384 * (4096 + u2 * (-768 + u2 * (320 - 175 * u2)))
    B = u2 / 1024 * (256 + u2 * (-128 + u2 * (74 - 47 * u2)))
    ds = B * ss * (c2sm + B / 4 * (cs * (-1 + 2 * c2sm ** 2)
                                   - B / 6 * c2sm * (-3 + 4 * ss ** 2) * (-3 + 4 * c2sm ** 2)))
    return b * A * (sigma - ds)


def geodesic_m(body, lat1, lon1, lat2, lon2):
    """The right yardstick for the body: ellipsoidal for Earth, spherical for the other four."""
    if body.lower() == "earth":
        return vincenty_m(lat1, lon1, lat2, lon2)
    return great_circle_m(lat1, lon1, lat2, lon2, reproject.body_radius_m(body))


# ------------------------------------------------------------------ the body definitions

def test_the_two_body_lists_partition_the_five_bodies():
    """The analytic claim is five bodies; the REAL-DATA claim is two. Keep them from merging."""
    assert set(ANALYTIC_BODIES) == {"earth", "mars", "moon", "mercury", "ceres"}
    assert set(REAL_DATA_BODIES) | set(SYNTHETIC_ONLY_BODIES) == set(ANALYTIC_BODIES)
    assert not (set(REAL_DATA_BODIES) & set(SYNTHETIC_ONLY_BODIES))
    require("mercury" not in REAL_DATA_BODIES and "ceres" not in REAL_DATA_BODIES,
            "a real Mercury or Ceres DEM appeared, which would change what may be claimed")


def test_every_body_declares_a_radius_and_a_geographic_crs():
    expect = {"earth": 6371008.8, "mars": 3396190.0, "moon": 1737400.0,
              "mercury": 2439400.0, "ceres": 469730.0}
    for body, r in expect.items():
        assert abs(reproject.body_radius_m(body) - r) < 1e-6, body
        crs = reproject.geographic_crs(body)
        if body == "earth":
            assert crs == "EPSG:4326"
        else:
            assert f"+a={r}" in crs and f"+b={r}" in crs, (
                f"{body}: the geographic CRS must carry the body's own radius, not Earth's")


def test_an_unknown_body_is_refused_rather_than_defaulted_to_earth():
    for fn in (reproject.body_radius_m, reproject.geographic_crs):
        try:
            fn("enceladus")
        except ValueError:
            pass
        else:
            raise AssertionError("an unknown body must be refused, never given Earth's geometry")
    try:
        reproject.local_aeqd(0.0, 0.0, "enceladus")
    except ValueError:
        pass
    else:
        raise AssertionError("local_aeqd must refuse an unknown body")


# ------------------------------------------------------------------ the defining property

def test_azimuthal_equidistant_is_geodesically_exact_on_all_five_bodies():
    """The invariant everything else rests on, checked against closed-form geodesy.

    Offsets include the axis directions AND the corners, because the corners are what the 9000 m
    footprint's diagonal is made of -- and a diagonal is where a projection that is only radial-
    exact would show up.
    """
    offsets = [(0.0, 0.0), (500.0, 0.0), (0.0, 500.0), (9000.0, 0.0), (0.0, 9000.0),
               (9000.0, 9000.0), (5000.0, 3000.0), (-4500.0, 4500.0), (0.0, -9000.0)]
    for body in ANALYTIC_BODIES:
        lat0, lon0 = SITE[body]
        crs = reproject.local_aeqd(lat0, lon0, body)
        geo = reproject.geographic_crs(body)
        xs = [o[0] for o in offsets]
        ys = [o[1] for o in offsets]
        lons, lats = _transform(crs, geo, xs, ys)
        for (dx, dy), lon2, lat2 in zip(offsets, lons, lats):
            want = math.hypot(dx, dy)
            got = geodesic_m(body, lat0, lon0, float(lat2), float(lon2))
            if want == 0.0:
                assert got < ORIGIN_TOL_M, (
                    f"{body}: the projection centre is {got:.4f} m from itself")
                continue
            assert abs(got - want) / want < ANGULAR_TOL, (
                f"{body}: a projected offset of {want:.1f} m is {got:.4f} m of geodesic distance "
                f"-- {abs(got - want):.4f} m off, which breaks the property 'a 500 m cell is 500 m "
                f"of ground' on this body")
        # and the property must not be a coincidence of one direction: every axis agrees
        for dx, dy in ((9000.0, 0.0), (0.0, 9000.0), (-9000.0, 0.0), (0.0, -9000.0)):
            lat2, lon2 = _one(crs, geo, dx, dy)
            err = abs(geodesic_m(body, lat0, lon0, lat2, lon2) - 9000.0)
            assert err / 9000.0 < ANGULAR_TOL, (
                f"{body}: the {dx},{dy} axis direction is {err:.4f} m off")


def _one(src, dst, x, y):
    """One transformed point, returned as (lat, lon) -- the order the geodesy functions take."""
    lons, lats = _transform(src, dst, [x], [y])
    return float(lats[0]), float(lons[0])


def test_the_lunar_site_is_validated_at_the_pole_not_at_a_convenient_latitude():
    """The real lunar data is at -89.46 deg. A projection check at the equator proves nothing there."""
    lat0, lon0 = SITE["moon"]
    assert lat0 < -89.0, "the lunar site moved away from the pole; re-check the extreme case"
    crs = reproject.local_aeqd(lat0, lon0, "moon")
    geo = reproject.geographic_crs("moon")
    lons, lats = _transform(crs, geo, [6364.0], [6364.0])     # a 9 km footprint's corner
    got = geodesic_m("moon", lat0, lon0, float(lats[0]), float(lons[0]))
    assert abs(got - math.hypot(6364.0, 6364.0)) / math.hypot(6364.0, 6364.0) < ANGULAR_TOL


def test_the_round_trip_returns_the_same_point_on_every_body():
    for body in ANALYTIC_BODIES:
        lat0, lon0 = SITE[body]
        crs = reproject.local_aeqd(lat0, lon0, body)
        geo = reproject.geographic_crs(body)
        lons, lats = _transform(crs, geo, [1234.5], [-6789.0])
        bx, by = _transform(geo, crs, [float(lons[0])], [float(lats[0])])
        assert abs(float(bx[0]) - 1234.5) < 1e-3 and abs(float(by[0]) + 6789.0) < 1e-3, (
            f"{body}: round trip lost the point ({bx[0]}, {by[0]})")


def test_a_body_scale_mistake_would_be_caught_by_this_check():
    """Negative control: a wrong radius must produce an error far above the tolerance.

    Without this, a five-body pass could just be a tolerance that is too generous to notice
    anything. Recomputing Earth's offsets on the MOON's radius is the mistake body-aware geometry
    exists to prevent, and it must be visible by orders of magnitude.
    """
    lat0, lon0 = SITE["earth"]
    crs = reproject.local_aeqd(lat0, lon0, "earth")
    geo = reproject.geographic_crs("earth")
    lons, lats = _transform(crs, geo, [9000.0], [0.0])
    right = geodesic_m("earth", lat0, lon0, float(lats[0]), float(lons[0]))
    wrong = great_circle_m(lat0, lon0, float(lats[0]), float(lons[0]),
                           reproject.body_radius_m("moon"))
    assert abs(wrong - 9000.0) > 1000.0, (
        "using the Moon's radius for an Earth offset must be wildly wrong, or the tolerance above "
        "is not testing anything")
    assert abs(right - 9000.0) / 9000.0 < ANGULAR_TOL


# ------------------------------------------------------------------ the grid arithmetic

def test_the_grid_arithmetic_is_body_independent_and_the_crs_is_not():
    """The plan and the coefficients are arithmetic; only the CRS knows which body it is on.

    That is a property worth pinning: if the coefficients varied by body, two sides of a comparison
    could disagree about what "500 m" means while both records looked well formed.
    """
    for support, n in PROJECT_FOOTPRINTS:
        want = (support, 0.0, -n * support / 2.0, 0.0, -support, n * support / 2.0)
        crs_seen = set()
        for body in ANALYTIC_BODIES:
            lat0, lon0 = SITE[body]
            crs, coeffs, half = cg.destination_grid(lat0, lon0, body, support, n)
            assert coeffs == want, f"{body}: coefficients {coeffs} != {want}"
            assert half == n * support / 2.0
            crs_seen.add(crs)
        assert len(crs_seen) == len(ANALYTIC_BODIES), "the CRS must differ per body"


def test_plan_refuses_an_inexact_grid_on_every_body():
    for footprint, support in ((9000.0, 700.0), (60000.0, 1750.0), (1.0, 3.0)):
        try:
            cg.plan(footprint, support)
        except cg.ComparabilityError:
            continue
        raise AssertionError(f"{footprint} m is not a whole number of {support} m cells")


def test_the_grid_centre_is_the_projection_origin_exactly():
    """Pixel-centre alignment, algebraically: the centre of an n x n grid maps to (0, 0).

    A half-cell offset here is invisible in a single window and shifts every comparison by half a
    cell in a way no per-unit record would show.
    """
    for support, n in PROJECT_FOOTPRINTS:
        a, b, c, d, e, f = (support, 0.0, -n * support / 2.0, 0.0, -support, n * support / 2.0)
        cx = a * (n / 2.0) + b * (n / 2.0) + c
        cy = d * (n / 2.0) + e * (n / 2.0) + f
        assert abs(cx) < 1e-9 and abs(cy) < 1e-9, f"{support}/{n}: grid centre maps to ({cx}, {cy})"


def test_the_physical_footprint_is_identical_for_every_body_and_support():
    for support, n in PROJECT_FOOTPRINTS:
        for body in ANALYTIC_BODIES:
            crs, coeffs, half = cg.destination_grid(*SITE[body], body, support, n)
            span = n * support
            assert abs(half - span / 2.0) < 1e-9
            assert abs(abs(coeffs[0]) - support) < 1e-9, "x scale is not the requested support"
            assert abs(abs(coeffs[4]) - support) < 1e-9, "y scale is not the requested support"


def test_the_shipped_lunar_footprint_fits_inside_a_lola_tile_on_every_body():
    """The 9000 m choice was forced by a rotated square inside a 16 km tile -- same geometry anywhere."""
    half = 9000.0 / 2.0
    assert 2 * half * math.sqrt(2) / 2 < 8000.0, (
        "the rotated 9000 m footprint's corner must stay inside the 16 km tile's half-extent")


def test_the_body_radius_map_matches_the_declared_canonical_values():
    """A radius typo is the cheapest way to corrupt every metric on a body."""
    for body, r in (("mars", reproject.MARS_RADIUS_M), ("moon", reproject.MOON_RADIUS_M),
                    ("mercury", reproject.MERCURY_RADIUS_M), ("ceres", reproject.CERES_RADIUS_M)):
        assert reproject.body_radius_m(body) == r
        assert f"+a={r}" in reproject.local_aeqd(0.0, 0.0, body)
    # and the four radii are distinct, so a lookup cannot be silently returning one of them
    assert len({reproject.MARS_RADIUS_M, reproject.MOON_RADIUS_M,
                reproject.MERCURY_RADIUS_M, reproject.CERES_RADIUS_M}) == 4
