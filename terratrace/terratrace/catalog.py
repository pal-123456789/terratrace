"""Machine-readable registry of the data sources TerraTrace can ingest.

A small STAC-like catalog so adding a source is structured and citeable, and so
`sources.lock.yml` / the UI can describe exactly what each product is, how it is
accessed, under what terms, and *where it is valid*. Facts here are verified
against provider docs; the exact product retrieved at run time is still pinned in
sources.lock.yml.

Each source also declares spatial `coverage` and a sensible output resolution
range so a preflight check can reject an AOI that the source cannot serve before
any bytes are downloaded, and `recommend_source` can pick the right product for a
bbox + target support without a human guessing.
"""
from __future__ import annotations

# Approximate lon/lat extents (west, south, east, north) for US 3DEP coverage.
# Honest and deliberately conservative; used only for fail-fast coverage checks.
_CONUS = (-124.8, 24.4, -66.9, 49.4)
_ALASKA = (-180.0, 51.0, -129.0, 71.6)      # Aleutian antimeridian wrap not modeled
_HAWAII = (-160.3, 18.9, -154.8, 22.3)
_PUERTO_RICO = (-67.3, 17.9, -65.2, 18.6)
_US_3DEP_BBOXES = [_CONUS, _ALASKA, _HAWAII, _PUERTO_RICO]
_EARTH_GLOBAL = [(-180.0, -90.0, 180.0, 90.0)]

SOURCES = {
    "mars_mola_megdr": {
        "id": "mars_mola_megdr", "body": "mars", "provider": "NASA PDS Geosciences / MGS MOLA",
        "product": "MOLA MEGDR gridded topography", "native_resolution_m": 463.0,
        "access": {"method": "download", "endpoint": "https://pds-geosciences.wustl.edu/missions/mgs/megdr.html"},
        "crs": "Mars 2000 sphere (R=3,396,190 m)", "vertical_datum": "Mars areoid",
        "key_required": False, "license": "NASA/PDS public; attribution required",
        "citation": "Smith et al., MGS MOLA MEGDR (NASA PDS Geosciences Node)",
        "coverage": {"kind": "global_body", "body": "mars", "complete": True,
                     "valid_resolution_range_m": [463.0, 500000.0],
                     "description": "Entire planet (polar gaps filled by interpolation)"},
    },
    "mars_mola_usgs_463m": {
        "id": "mars_mola_usgs_463m", "body": "mars", "provider": "USGS Astrogeology",
        "product": "Mars MGS MOLA DEM 463m (GeoTIFF)", "native_resolution_m": 463.0,
        "access": {"method": "download",
                   "endpoint": "https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m"},
        "crs": "Mars equirectangular", "vertical_datum": "Mars areoid",
        "key_required": False, "license": "USGS/NASA public; attribution requested",
        "citation": "USGS Astrogeology, Mars MGS MOLA DEM 463 m",
        "coverage": {"kind": "global_body", "body": "mars", "complete": True,
                     "valid_resolution_range_m": [463.0, 500000.0],
                     "description": "Entire planet, equirectangular GeoTIFF"},
    },
    "earth_cop30": {
        "id": "earth_cop30", "body": "earth", "provider": "ESA Copernicus via OpenTopography",
        "product": "Copernicus GLO-30 DSM", "native_resolution_m": 30.0,
        "access": {"method": "opentopography_globaldem",
                   "endpoint": "https://portal.opentopography.org/API/globaldem", "demtype": "COP30"},
        "crs": "EPSG:4326", "vertical_datum": "EGM2008 (approx)",
        "key_required": True, "license": "Copernicus; free use with attribution",
        "citation": "(c) ESA Copernicus GLO-30 DSM, via OpenTopography",
        "coverage": {"kind": "global_land", "bboxes": _EARTH_GLOBAL, "complete": True,
                     "valid_resolution_range_m": [30.0, 500000.0],
                     "description": "Global land; ocean returns sea-level/nodata (use a water mask)"},
    },
    "earth_usgs10m": {
        "id": "earth_usgs10m", "body": "earth", "provider": "USGS 3DEP via OpenTopography",
        "product": "3DEP 1/3 arc-second seamless DEM (~10 m)", "native_resolution_m": 10.0,
        "access": {"method": "opentopography_usgsdem",
                   "endpoint": "https://portal.opentopography.org/API/usgsdem", "datasetName": "USGS10m"},
        "crs": "EPSG:4326", "vertical_datum": "NAVD88 (approx)",
        "key_required": True, "license": "U.S. public domain (3DEP); attribution requested",
        "citation": "USGS 3DEP 1/3 arc-second DEM (DOI:10.5069/G98K778D)",
        "coverage": {"kind": "regional", "bboxes": _US_3DEP_BBOXES, "complete": True,
                     "valid_resolution_range_m": [10.0, 100000.0],
                     "description": "United States: CONUS, AK, HI, PR (seamless)"},
    },
    "earth_usgs1m": {
        "id": "earth_usgs1m", "body": "earth", "provider": "USGS 3DEP (TNM / ImageServer)",
        "product": "3DEP 1 m lidar-derived DEM", "native_resolution_m": 1.0,
        "access": {"method": "tnm_or_imageserver",
                   "endpoint": "https://elevation.nationalmap.gov/arcgis/rest/services/3DEPElevation/ImageServer/exportImage"},
        "crs": "request bbox EPSG:4326; output CRS = ImageServer default", "vertical_datum": "NAVD88 (approx)",
        "key_required": False, "license": "U.S. public domain (3DEP); attribution requested",
        "citation": "USGS 3DEP 1 m DEM (DOI:10.5069/G9NP22NT)",
        "coverage": {"kind": "regional_partial", "bboxes": _US_3DEP_BBOXES, "complete": False,
                     "valid_resolution_range_m": [1.0, 10000.0],
                     "description": "United States, lidar extent only (NOT continuous; verify tile exists)"},
    },
}

REQUIRED_FIELDS = ("id", "body", "provider", "product", "native_resolution_m",
                   "access", "crs", "vertical_datum", "key_required", "license",
                   "citation", "coverage")


def all_ids():
    return sorted(SOURCES)


def get(source_id):
    if source_id not in SOURCES:
        raise KeyError(f"unknown source {source_id!r}; known: {all_ids()}")
    return SOURCES[source_id]


def by_body(body):
    return [s for s in SOURCES.values() if s["body"] == body.lower()]


def _bbox_inside(inner, outer):
    """True if (w,s,e,n) `inner` lies fully within `outer` (both lon/lat degrees)."""
    iw, is_, ie, in_ = inner
    ow, os_, oe, on_ = outer
    return iw >= ow and ie <= oe and is_ >= os_ and in_ <= on_


def source_covers(source_id, bbox, body=None):
    """Does `source_id` serve `bbox` (west,south,east,north, degrees) for `body`?

    Returns {covered, complete, reason}. `complete` is False for sources whose
    footprint is advertised but not continuous (e.g. 1 m lidar), so a caller can
    treat coverage as advisory and still verify a tile exists before fieldwork.
    """
    s = get(source_id)
    cov = s["coverage"]
    if body is not None and body.lower() != s["body"]:
        return {"covered": False, "complete": False,
                "reason": f"body mismatch: source is {s['body']!r}, requested {body!r}"}
    if cov["kind"] == "global_body":
        return {"covered": True, "complete": bool(cov.get("complete", True)),
                "reason": f"{s['body']}-global product covers the whole planet"}
    for ob in cov.get("bboxes", []):
        if _bbox_inside(bbox, ob):
            complete = bool(cov.get("complete", True))
            note = "" if complete else " (footprint advertised but NOT continuous — verify tile)"
            return {"covered": True, "complete": complete,
                    "reason": f"inside {cov['description']}{note}"}
    return {"covered": False, "complete": False,
            "reason": f"bbox outside coverage: {cov['description']}"}


def recommend_source(bbox, body, target_support_m, require_keyless=False):
    """Pick the best catalog source for a bbox + target common support.

    Preference, among sources that cover the bbox for `body`:
      1. native resolution fine enough to aggregate UP to target_support_m
         (native <= target); of those, the one CLOSEST to target (coarsest that
         still qualifies) to minimise download while meeting the support;
      2. if none qualify, the finest available, with a warning that the target
         support is finer than any covered source can provide.
    Complete-coverage sources are preferred over advertised-but-partial ones at
    equal resolution. Returns {source_id, reason, warnings, candidates}.
    """
    warnings = []
    scored = []
    partial_reason = {}
    for s in by_body(body):
        if require_keyless and s["key_required"]:
            continue
        cov = source_covers(s["id"], bbox, body)
        if not cov["covered"]:
            continue
        if not cov["complete"]:
            partial_reason[s["id"]] = cov["reason"]   # noted; warned only if CHOSEN
        scored.append((s["id"], float(s["native_resolution_m"]), bool(cov["complete"])))
    if not scored:
        return {"source_id": None, "reason": "no covered source for this bbox/body",
                "warnings": warnings, "candidates": []}
    qualifying = [t for t in scored if t[1] <= target_support_m]
    if qualifying:
        # coarsest native <= target; break ties toward complete coverage, then id.
        qualifying.sort(key=lambda t: (-t[1], not t[2], t[0]))
        best = qualifying[0]
        reason = (f"native {best[1]:g} m <= target support {target_support_m:g} m; "
                  f"closest-to-target among covered sources (minimises download)")
    else:
        scored.sort(key=lambda t: (t[1], not t[2], t[0]))
        best = scored[0]
        warnings.append(f"target support {target_support_m:g} m is finer than any covered "
                        f"source; finest available is {best[0]} at {best[1]:g} m")
        reason = f"no source reaches {target_support_m:g} m; finest covered = {best[1]:g} m"
    # Only warn about partial coverage for the source we actually recommend.
    if best[0] in partial_reason:
        warnings.append(f"{best[0]}: {partial_reason[best[0]]}")
    return {"source_id": best[0], "reason": reason, "warnings": warnings,
            "candidates": sorted(t[0] for t in scored)}


def _coverage_problems(sid, cov):
    probs = []
    if not isinstance(cov, dict):
        return [(sid, "coverage not a dict")]
    kind = cov.get("kind")
    if kind not in ("global_body", "global_land", "regional", "regional_partial"):
        probs.append((sid, f"coverage.kind unknown: {kind!r}"))
    if kind != "global_body":
        bbs = cov.get("bboxes")
        if not isinstance(bbs, list) or not bbs:
            probs.append((sid, "coverage.bboxes missing/empty"))
        else:
            for b in bbs:
                if not (isinstance(b, (list, tuple)) and len(b) == 4):
                    probs.append((sid, f"coverage bbox not 4-tuple: {b!r}"))
    rng = cov.get("valid_resolution_range_m")
    if not (isinstance(rng, (list, tuple)) and len(rng) == 2 and rng[0] <= rng[1]):
        probs.append((sid, f"valid_resolution_range_m invalid: {rng!r}"))
    return probs


def validate():
    """Return a list of (id, problem) for any registry entry that is missing a
    field, has the wrong type, or an out-of-domain value."""
    problems = []
    for sid, s in SOURCES.items():
        if s.get("id") != sid:
            problems.append((sid, "id field mismatch"))
        for f in REQUIRED_FIELDS:
            if f not in s:
                problems.append((sid, f"missing field {f}"))
        acc = s.get("access")
        if not isinstance(acc, dict) or "method" not in acc:
            problems.append((sid, "access.method missing"))
        if s.get("body") not in ("mars", "earth"):
            problems.append((sid, f"body not in mars/earth: {s.get('body')!r}"))
        res = s.get("native_resolution_m")
        if not isinstance(res, (int, float)) or res <= 0:
            problems.append((sid, f"native_resolution_m not positive: {res!r}"))
        if not isinstance(s.get("key_required"), bool):
            problems.append((sid, "key_required not bool"))
        if "coverage" in s:
            problems.extend(_coverage_problems(sid, s["coverage"]))
    return problems