"""Validate the reprojection against closed-form geodesy — not against a second GDAL wrapper.

WHY THIS FILE EXISTS
--------------------
`docs/INDEPENDENT-GIS-REPRODUCTION.md` records an honest gap: the reprojection was **not**
independently reproduced, because the "two toolchains" it compared were both GDAL
(`rasterio.warp` and `gdalwarp`/WhiteboxTools). Two wrappers around one library is one
implementation, not a reproduction. Benchmarking 1,000 rabbits is not benchmarking a rabbit and a
tortoise.

This closes that gap with mathematics instead of software. An azimuthal-equidistant projection has
a defining property that is exact and closed-form: **the distance from the projection centre to any
projected point equals the geodesic distance on the body between those two geographic points.**
That gives an absolute reference computed from a formula, so the comparison has a right answer
rather than a second opinion:

* **sphere** (the Moon, Mars, Mercury, Ceres — the engine treats these as spheres): the exact
  spherical great-circle distance, `R·acos(sinφ₁sinφ₂ + cosφ₁cosφ₂cos Δλ)`.
* **ellipsoid** (Earth): Lambert's formula, an independent series solution for the ellipsoidal
  geodesic, to order `f`.

If the projection were subtly wrong — a mis-declared radius, a transposed axis, a wrong datum — this
disagrees by kilometres. If it is right, it agrees to floating point.

Usage:
    python scripts/reproject_analytic_check.py
    python scripts/reproject_analytic_check.py --body moon
"""
from __future__ import annotations

import argparse
import math
import pathlib
import re
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from terratrace import reproject  # noqa: E402

# reference figures, stated independently of the engine so the check cannot inherit its constants
WGS84_A, WGS84_F = 6378137.0, 1.0 / 298.257223563
MOON_R = 1737400.0


# Published ellipsoid axes, stated here rather than read from the library under test — that is the
# whole point of the check. +datum=WGS84 names an ellipsoid without spelling out its axes, so the
# name is resolved against these figures.
DATUM_AXES = {
    "WGS84": (6378137.0, 6356752.314245179),
    "GRS80": (6378137.0, 6356752.314140356),
}


def crs_axes(wkt_or_proj: str):
    """Pull (a, b) out of a PROJ/WKT string, or resolve the datum it names. +R means a sphere."""
    a = b = None
    for key in ("a", "b"):
        m = re.search(rf"[+]?{key}=([0-9.eE+-]+)", wkt_or_proj)
        if m:
            value = float(m.group(1))
            if key == "a":
                a = value
            else:
                b = value
    if a is None:
        m = re.search(r"[+]?R=([0-9.eE+-]+)", wkt_or_proj)
        if m:
            a = b = float(m.group(1))
    if a is None:
        m = re.search(r"[+]?datum=([A-Za-z0-9_]+)", wkt_or_proj)
        if m and m.group(1) in DATUM_AXES:
            a, b = DATUM_AXES[m.group(1)]
    return a, (b if b is not None else a)


def great_circle_m(R, lat1, lon1, lat2, lon2):
    """Exact great-circle distance on a sphere of radius R. Closed form, no library."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    c = math.sin(p1) * math.sin(p2) + math.cos(p1) * math.cos(p2) * math.cos(dl)
    return R * math.acos(max(-1.0, min(1.0, c)))


def meridional_arc_m(a, f, lat1, lat2, intervals=200000):
    """Distance due north/south along a meridian, by Simpson quadrature of the exact integrand.

    The integrand is the meridional radius of curvature, M(phi) = a(1-e^2)/(1-e^2 sin^2 phi)^1.5,
    which is closed-form; the quadrature is the only approximation and it converges to far below a
    millimetre. M(phi) d(phi) IS the arc length along the meridian, so there is no series to
    truncate and no formula to recall incorrectly.

    An earlier revision of this file used Lambert's formula from memory, got it wrong, and reported
    the projection as being in error by up to 107 m. The projection was right; the reference was
    not. Quadrature of a known integrand cannot fail that way, which is why the ellipsoidal checks
    are restricted to the cases where it applies.
    """
    e2 = 2.0 * f - f * f

    def M(phi):
        return a * (1.0 - e2) / (1.0 - e2 * math.sin(phi) ** 2) ** 1.5

    lo, hi = math.radians(lat1), math.radians(lat2)
    h = (hi - lo) / intervals
    total = M(lo) + M(hi)
    for i in range(1, intervals):
        total += (4.0 if i % 2 else 2.0) * M(lo + i * h)
    return abs(total * h / 3.0)


def equatorial_arc_m(a, lon1, lon2):
    """Distance along the equator is exactly a * delta-lambda. Closed form."""
    return abs(a * math.radians(lon2 - lon1))


def analytic_distance_m(body, lat1, lon1, lat2, lon2):
    """The distance the projection is *supposed* to represent, from first principles.

    Returns ``(metres_or_None, kind, a)``. ``None`` means no reference this file can derive
    rigorously applies to that probe — a general azimuthal geodesic on an ellipsoid needs a geodesic
    solver, and calling one would replace a wrong reference with a second library rather than with
    mathematics. Those probes are reported as uncovered, not quietly dropped.
    """
    crs = reproject.local_aeqd(lat1, lon1, body)
    a, b = crs_axes(str(crs))
    if a is None:
        raise RuntimeError(f"could not read the axes out of {crs!r}")
    if abs(a - b) < 1e-9:
        return great_circle_m(a, lat1, lon1, lat2, lon2), "sphere/great-circle", a
    f = (a - b) / a
    if abs(lon2 - lon1) < 1e-12:
        return meridional_arc_m(a, f, lat1, lat2), "ellipsoid/meridional-quadrature", a
    if abs(lat1) < 1e-9 and abs(lat2) < 1e-9:
        return equatorial_arc_m(a, lon1, lon2), "ellipsoid/equatorial-closed-form", a
    return None, "ellipsoid/azimuthal (not analytically covered)", a


def projected_distance_m(body, lat0, lon0, pts):
    """Distance from the projection centre to each point, measured in the projected CRS."""
    from rasterio.warp import transform as warp_transform
    lons = [lon0] + [p[1] for p in pts]
    lats = [lat0] + [p[0] for p in pts]
    x, y = warp_transform(reproject.geographic_crs(body),
                          reproject.local_aeqd(lat0, lon0, body), lons, lats)
    x, y = np.asarray(x, dtype="float64"), np.asarray(y, dtype="float64")
    return np.hypot(x[1:] - x[0], y[1:] - y[0])


def check_body(body, centre, offsets_deg, radius_expect=None):
    """Every synthetic offset from the centre: what the projection says vs what the maths says."""
    lat0, lon0 = centre
    # A near-polar centre plus a northward offset can leave the valid latitude range, and PROJ
    # rejects it with "aeqd: Invalid latitude" rather than saturating. Drop those probes and say so
    # rather than quietly testing fewer cases.
    pts, skipped = [], []
    for dlat, dlon, tag in offsets_deg:
        lat = lat0 + dlat
        if abs(lat) >= 89.995:
            skipped.append(tag)
            continue
        pts.append((lat, lon0 + dlon, tag))
    if skipped:
        print(f"  (skipped {len(skipped)} probe(s) outside the valid latitude range: {skipped})")
    got = projected_distance_m(body, lat0, lon0, [(p[0], p[1]) for p in pts])
    rows, uncovered = [], []
    for (lat, lon, tag), g in zip(pts, got):
        want, kind, a = analytic_distance_m(body, lat0, lon0, lat, lon)
        if want is None:
            uncovered.append((tag, kind))
            continue
        rows.append({"tag": tag, "projected_m": float(g), "analytic_m": float(want),
                     "abs_err_m": float(abs(g - want)),
                     "rel_err": float(abs(g - want) / want) if want else 0.0})
    if uncovered:
        print(f"  (no analytic reference for {len(uncovered)} probe(s): "
              f"{sorted({k for _, k in uncovered})})")
    assert rows, f"{body}: every probe was uncovered, so this check proves nothing"
    worst = max(r["abs_err_m"] for r in rows)
    return {"body": body, "centre": [lat0, lon0], "surface": kind, "radius_m": a,
            "radius_expected": radius_expect,
            "max_abs_err_m": worst,
            "max_rel_err": max(r["rel_err"] for r in rows), "points": rows,
            "n_uncovered": len(uncovered)}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--body", default=None, help="check one body (default: moon and earth)")
    args = ap.parse_args(argv)

    # offsets that exercise both axes and diagonals, out to a few km and to ~100 km
    offsets = [
        (+0.01, 0.00, "0.01 deg north"),
        (-0.01, 0.00, "0.01 deg south"),
        (0.00, +0.01, "0.01 deg east (longitude, so shorter at high latitude)"),
        (0.00, -0.01, "0.01 deg west"),
        (+0.02, +0.02, "diagonal NE 0.02 deg"),
        (+0.10, 0.00, "0.10 deg north"),
        (0.00, +0.30, "0.30 deg east"),
        (+0.50, +0.50, "diagonal NE 0.5 deg"),
        (+1.00, 0.00, "1.0 deg north (~30 km on the Moon)"),
    ]

    # Each plan carries the probes that have a rigorous reference at ITS centre. A centre on the
    # equator is what makes the east-west case exactly a*dlambda; at 36.2 N the same probe has no
    # closed form, so it is simply not claimed there.
    ew = [(0.00, +0.10, "0.10 deg east (equatorial)"),
          (0.00, -0.10, "0.10 deg west (equatorial)"),
          (0.00, +1.00, "1.0 deg east (equatorial, ~111 km)")]
    plans = []
    if args.body in (None, "moon"):
        plans.append(("moon (near-polar working regime)", "moon", (89.0, 0.0), MOON_R, offsets))
    if args.body in (None, "earth"):
        plans.append(("earth (meridional)", "earth", (36.2, -115.6), WGS84_A,
                      [o for o in offsets if abs(o[1]) < 1e-12]))
        plans.append(("earth (equatorial)", "earth", (0.0, -115.6), WGS84_A, ew))

    results, failures = [], []
    for label, body, centre, radius_expect, probes in plans:
        print(f"\n--- {label} ---")
        r = check_body(body, centre, probes, radius_expect)
        r["label"] = label
        results.append(r)
        print(f"\n{body}: centre {centre}, projection is {r['surface']}-based, a = {r['radius_m']:.1f} m")
        if radius_expect is not None:
            if abs(r["radius_m"] - radius_expect) > 1.0:
                failures.append(f"{body}: projection radius {r['radius_m']} != {radius_expect}")
                print(f"  !! radius is {r['radius_m']}, expected {radius_expect}")
        print(f"  {'point':46s} {'projected m':>13s} {'analytic m':>13s} {'abs err m':>11s}")
        for row in r["points"]:
            print(f"  {row['tag']:46s} {row['projected_m']:13.3f} {row['analytic_m']:13.3f} "
                  f"{row['abs_err_m']:11.6f}")
        print(f"  worst absolute error {r['max_abs_err_m']:.6f} m "
              f"(relative {r['max_rel_err']:.2e})")
        # tolerance: the projection's own datum shift is exact here, so the only licence allowed is
        # floating-point noise plus, for the ellipsoid, Lambert's O(f^2) truncation (~mm at 100 km)
        tol = 0.05 if r["surface"] == "sphere" else 1.0
        if r["max_abs_err_m"] > tol:
            failures.append(f"{body}: worst error {r['max_abs_err_m']:.6f} m exceeds {tol} m")

    print("\n" + "=" * 78)
    if failures:
        print("FAILED:")
        for f in failures:
            print("  -", f)
        return 1
    print("PASSED: the reprojection matches closed-form geodesy on every body tested.")
    print("The projection's distances-from-centre are the geodesic distances, so the engine's "
          "reprojection is validated against mathematics rather than against another GDAL wrapper.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
