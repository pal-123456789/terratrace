"""Fail-fast preflight checks for a TerraTrace AOI configuration.

Before any bytes are downloaded or any study is run, this module answers two
cheap questions for every terrain unit in a config: "is the bounding box even
well-formed for its body?" and "roughly how big is the request?". It leans on
`catalog.recommend_source` to pick the product that actually covers a bbox, so a
non-US AOI is never silently pointed at a US-only 3DEP product.

HONESTY CAVEATS (read before trusting a number):
  * Area / pixel / download numbers are APPROXIMATE. We use a planar
    cosine-latitude box area (mean-latitude scaling of longitude), not a true
    geodesic/ellipsoidal integral, and we assume square native pixels. Treat
    them as order-of-magnitude sizing to catch "this is 10x too big", not as
    exact byte counts.
  * Coverage for partial sources (e.g. USGS 3DEP 1 m lidar) is ADVISORY. A
    source whose footprint is advertised but not continuous may still have NO
    tile over a given bbox; `catalog` marks these incomplete and we surface the
    warning, but preflight passing is NOT a guarantee a tile exists.
  * The size limits are HEURISTIC practical ceilings (loosely modelling
    OpenTopography request limits and local disk/RAM budgets), so exceeding one
    is a WARNING, not a hard failure -- the caller may still choose to proceed.
"""
from __future__ import annotations

import math

from . import catalog

# Body mean radii used for the planar area approximation (km).
_R_EARTH_KM = 6371.0
_R_MARS_KM = 3396.19          # Mars 2000 sphere, matches MOLA catalog CRS

# Heuristic practical ceilings. These are deliberately round, approximate limits
# (not provider-exact) so a wildly oversized AOI is flagged before download.
_DEFAULT_LIMITS = {
    "max_download_mb": 500.0,
    "max_pixels": 1e8,
    "max_area_km2": 2.5e5,
}


def _radius_km(body):
    """Mars uses its own sphere radius; everything else is treated as Earth."""
    return _R_MARS_KM if str(body).lower() == "mars" else _R_EARTH_KM


def validate_bbox(bbox, body):
    """Return a list of problem strings for `bbox` on `body` (empty == valid).

    Longitude domain is body-specific: Mars MOLA products ship in either 0..360
    or -180..180, so we accept the union [-180, 360]; Earth uses the usual
    [-180, 180]. Strict ordering (west < east, south < north) is required, which
    also rejects a degenerate zero-span box.
    """
    problems = []
    b = str(body).lower() if body is not None else ""
    if b not in ("mars", "earth"):
        problems.append(f"body must be 'mars' or 'earth', got {body!r}")

    # Structural check first; without 4 numbers nothing else is meaningful.
    if not isinstance(bbox, (list, tuple)) or len(bbox) != 4:
        problems.append(f"bbox must be 4 numbers (west,south,east,north), got {bbox!r}")
        return problems
    try:
        west, south, east, north = (float(v) for v in bbox)
    except (TypeError, ValueError):
        problems.append(f"bbox values must be numbers, got {bbox!r}")
        return problems

    # Strict ordering doubles as the non-degenerate (positive span) check.
    if not west < east:
        problems.append(f"west ({west:g}) must be < east ({east:g}) -- degenerate/empty span")
    if not south < north:
        problems.append(f"south ({south:g}) must be < north ({north:g}) -- degenerate/empty span")

    for name, lat in (("south", south), ("north", north)):
        if not -90.0 <= lat <= 90.0:
            problems.append(f"{name} latitude {lat:g} out of range [-90, 90]")

    # Only range-check longitude once the body's convention is known.
    lon_bounds = {"mars": (-180.0, 360.0), "earth": (-180.0, 180.0)}.get(b)
    if lon_bounds is not None:
        lo, hi = lon_bounds
        for name, lon in (("west", west), ("east", east)):
            if not lo <= lon <= hi:
                problems.append(f"{name} longitude {lon:g} out of range [{lo:g}, {hi:g}] for {b}")
    return problems


def bbox_area_km2(bbox, body):
    """Approximate bbox area in km^2 via mean-latitude cosine scaling.

    Planar estimate: dlat_rad * dlon_rad * R^2 * cos(mean_lat). Good to a few
    percent for small mid-latitude boxes, increasingly rough toward the poles --
    deliberately an estimate, not a geodesic truth (see module caveats).
    """
    west, south, east, north = (float(v) for v in bbox)
    r_km = _radius_km(body)
    dlon_rad = math.radians(abs(east - west))
    dlat_rad = math.radians(abs(north - south))
    mean_lat_rad = math.radians((south + north) / 2.0)
    # cos is only negative past the poles; clamp so area can never go negative.
    return dlat_rad * dlon_rad * (r_km ** 2) * max(0.0, math.cos(mean_lat_rad))


def estimate_pixels(bbox, native_resolution_m, body):
    """Approximate pixel count = area_m2 / res^2 (assumes square native pixels)."""
    res = float(native_resolution_m)
    if res <= 0:                              # guard: a non-positive res has no meaning
        return 0
    area_m2 = bbox_area_km2(bbox, body) * 1e6
    return max(0, int(round(area_m2 / (res * res))))


def estimate_download_mb(n_pixels, bytes_per_pixel=4):
    """Approximate raw size in MB (default 4 bytes/pixel = a float32 DEM sample)."""
    return n_pixels * bytes_per_pixel / (1024 * 1024)


def preflight_unit(unit, body, target_support_m, limits=None):
    """Validate + size one config unit; see module docstring for honesty caveats.

    `ok` is True only when there are no hard problems. Size-limit breaches and
    partial-coverage notes are WARNINGS so a caller can still proceed knowingly.
    """
    limits = dict(_DEFAULT_LIMITS) if limits is None else dict(limits)
    uid = unit.get("id", "<unnamed>")
    bbox = unit.get("bbox")

    problems = validate_bbox(bbox, body)
    if problems:
        # A malformed bbox makes coverage + size estimates meaningless -> bail.
        return {"id": uid, "ok": False, "problems": problems, "warnings": [],
                "estimates": {}, "recommended_source": None}

    warnings = []
    # Let the catalog choose what actually covers this bbox (not the unit's wish),
    # so a non-US AOI can never resolve to a US-only product.
    recommended = catalog.recommend_source(bbox, body, target_support_m)
    warnings.extend(recommended.get("warnings", []))
    if recommended.get("source_id") is None:
        problems.append("no catalog source covers this bbox")

    # Resolution for sizing: the unit's declared posting wins (it is what gets
    # written); otherwise fall back to the recommended source's native posting.
    res_m = unit.get("native_posting_m")
    if res_m is None and recommended.get("source_id") is not None:
        res_m = catalog.get(recommended["source_id"])["native_resolution_m"]

    estimates = {}
    if res_m is not None:
        area_km2 = bbox_area_km2(bbox, body)
        pixels = estimate_pixels(bbox, res_m, body)
        download_mb = estimate_download_mb(pixels)
        estimates = {"resolution_m": float(res_m), "area_km2": area_km2,
                     "pixels": pixels, "download_mb": download_mb}
        # Approximate ceilings -> warnings only; name the number AND the limit.
        if area_km2 > limits["max_area_km2"]:
            warnings.append(f"approximate area {area_km2:,.0f} km^2 exceeds heuristic "
                            f"limit {limits['max_area_km2']:,.0f} km^2")
        if pixels > limits["max_pixels"]:
            warnings.append(f"estimated {pixels:,} pixels exceeds heuristic limit "
                            f"{int(limits['max_pixels']):,}")
        if download_mb > limits["max_download_mb"]:
            warnings.append(f"estimated download {download_mb:,.1f} MB exceeds heuristic "
                            f"limit {limits['max_download_mb']:,.0f} MB")

    return {"id": uid, "ok": not problems, "problems": problems, "warnings": warnings,
            "estimates": estimates, "recommended_source": recommended}


def preflight_config(cfg):
    """Preflight every unit in a parsed config dict (reference + earth_units).

    Returns {ok, units, problems, target_support_m}. `problems` is a flat list of
    "<unit_id>: <msg>" so a caller can print one list; `units` keeps the full
    per-unit result (estimates, warnings, recommended_source) for detail.
    """
    target_support_m = cfg.get("target_support_m", 1000.0)
    units = {}
    flat_problems = []

    # Read body per-unit rather than assuming, so a mixed config still validates:
    # the reference is usually Mars, each earth unit declares its own body.
    unit_specs = []
    ref = cfg.get("reference")
    if isinstance(ref, dict):
        unit_specs.append((ref, ref.get("body", "mars")))
    for u in cfg.get("earth_units", []):
        unit_specs.append((u, u.get("body", "earth")))

    for u, body in unit_specs:
        result = preflight_unit(u, body, target_support_m)
        units[result["id"]] = result
        for msg in result["problems"]:
            flat_problems.append(f"{result['id']}: {msg}")

    # all([]) is True, so an empty config is vacuously ok (nothing to download).
    ok = all(u["ok"] for u in units.values())
    return {"ok": ok, "units": units, "problems": flat_problems,
            "target_support_m": target_support_m}

