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
# SRTM-family radars flew on the Shuttle: coverage is the classic 60N - 56S band.
_SRTM_BAND = [(-180.0, -56.0, 180.0, 60.0)]

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
    "moon_lola_ldem": {
        "id": "moon_lola_ldem", "body": "moon", "provider": "NASA LRO LOLA / USGS Astrogeology",
        "product": "LRO LOLA LDEM global lunar topography (~118 m)", "native_resolution_m": 118.0,
        "access": {"method": "download",
                   "endpoint": "https://astrogeology.usgs.gov/search/map/lunar_lro_lola_global_ldem_118m"},
        "crs": "Moon 2000 sphere (R=1,737,400 m)", "vertical_datum": "Moon mean radius (selenoid)",
        "key_required": False, "license": "NASA/USGS public; attribution requested",
        "citation": "Smith et al., LRO LOLA LDEM; USGS Astrogeology lunar LDEM 118 m",
        "coverage": {"kind": "global_body", "body": "moon", "complete": True,
                     "valid_resolution_range_m": [118.0, 500000.0],
                     "description": "Entire Moon (LOLA laser altimetry; denser near the poles)"},
    },
    "mercury_messenger_dem": {
        "id": "mercury_messenger_dem", "body": "mercury", "provider": "NASA MESSENGER / USGS Astrogeology",
        "product": "Mercury MESSENGER global DEM (~665 m)", "native_resolution_m": 665.0,
        "access": {"method": "download",
                   "endpoint": "https://astrogeology.usgs.gov/search/map/mercury_messenger_usgs_dem_global_665m"},
        "crs": "Mercury 2000 sphere (R=2,439,400 m)", "vertical_datum": "Mercury mean radius",
        "key_required": False, "license": "NASA/USGS public; attribution requested",
        "citation": "USGS Astrogeology, Mercury MESSENGER global DEM 665 m (MLA + stereo)",
        "coverage": {"kind": "global_body", "body": "mercury", "complete": True,
                     "valid_resolution_range_m": [665.0, 500000.0],
                     "description": "Entire planet (MESSENGER stereo + MLA)"},
    },
    "ceres_dawn_dem": {
        "id": "ceres_dawn_dem", "body": "ceres", "provider": "NASA Dawn / USGS Astrogeology",
        "product": "Ceres Dawn HAMO DEM (~137 m)", "native_resolution_m": 137.0,
        "access": {"method": "download",
                   "endpoint": "https://astrogeology.usgs.gov/search/map/ceres_dawn_fc_hamo_dtm_global_60ppd"},
        "crs": "Ceres sphere (R=469,730 m)", "vertical_datum": "Ceres mean radius",
        "key_required": False, "license": "NASA/USGS public; attribution requested",
        "citation": "USGS Astrogeology, Ceres Dawn HAMO global DTM",
        "coverage": {"kind": "global_body", "body": "ceres", "complete": True,
                     "valid_resolution_range_m": [137.0, 500000.0],
                     "description": "Entire dwarf planet (Dawn Framing Camera HAMO)"},
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
    "earth_cop90": {
        "id": "earth_cop90", "body": "earth", "provider": "ESA Copernicus via OpenTopography",
        "product": "Copernicus GLO-90 DSM", "native_resolution_m": 90.0,
        "access": {"method": "opentopography_globaldem",
                   "endpoint": "https://portal.opentopography.org/API/globaldem", "demtype": "COP90"},
        "crs": "EPSG:4326", "vertical_datum": "EGM2008 (approx)",
        "key_required": True, "license": "Copernicus; free use with attribution",
        "citation": "(c) ESA Copernicus GLO-90 DSM, via OpenTopography",
        "coverage": {"kind": "global_land", "bboxes": _EARTH_GLOBAL, "complete": True,
                     "valid_resolution_range_m": [90.0, 500000.0],
                     "description": "Global land; ocean returns sea-level/nodata (use a water mask)"},
    },
    "earth_nasadem": {
        "id": "earth_nasadem", "body": "earth", "provider": "NASA/USGS via OpenTopography",
        "product": "NASADEM (reprocessed, void-filled SRTM, ~30 m)", "native_resolution_m": 30.0,
        "access": {"method": "opentopography_globaldem",
                   "endpoint": "https://portal.opentopography.org/API/globaldem", "demtype": "NASADEM"},
        "crs": "EPSG:4326", "vertical_datum": "EGM96 (approx)",
        "key_required": True, "license": "NASA/USGS public; attribution requested",
        "citation": "NASADEM Merged DEM Global 1 arc-second, via OpenTopography",
        "coverage": {"kind": "global_land", "bboxes": _SRTM_BAND, "complete": True,
                     "valid_resolution_range_m": [30.0, 500000.0],
                     "description": "Land between 60 deg N and 56 deg S (SRTM swath), void-filled"},
    },
    "earth_srtmgl1": {
        "id": "earth_srtmgl1", "body": "earth", "provider": "NASA SRTM via OpenTopography",
        "product": "SRTM GL1 Global 30 m DEM", "native_resolution_m": 30.0,
        "access": {"method": "opentopography_globaldem",
                   "endpoint": "https://portal.opentopography.org/API/globaldem", "demtype": "SRTMGL1"},
        "crs": "EPSG:4326", "vertical_datum": "EGM96 (approx)",
        "key_required": True, "license": "NASA public; attribution requested",
        "citation": "NASA Shuttle Radar Topography Mission GL1 (30 m), via OpenTopography",
        "coverage": {"kind": "global_land", "bboxes": _SRTM_BAND, "complete": True,
                     "valid_resolution_range_m": [30.0, 500000.0],
                     "description": "Land between 60 deg N and 56 deg S (SRTM swath); unfilled voids possible"},
    },
    "earth_srtmgl3": {
        "id": "earth_srtmgl3", "body": "earth", "provider": "NASA SRTM via OpenTopography",
        "product": "SRTM GL3 Global 90 m DEM", "native_resolution_m": 90.0,
        "access": {"method": "opentopography_globaldem",
                   "endpoint": "https://portal.opentopography.org/API/globaldem", "demtype": "SRTMGL3"},
        "crs": "EPSG:4326", "vertical_datum": "EGM96 (approx)",
        "key_required": True, "license": "NASA public; attribution requested",
        "citation": "NASA Shuttle Radar Topography Mission GL3 (90 m), via OpenTopography",
        "coverage": {"kind": "global_land", "bboxes": _SRTM_BAND, "complete": True,
                     "valid_resolution_range_m": [90.0, 500000.0],
                     "description": "Land between 60 deg N and 56 deg S (SRTM swath); unfilled voids possible"},
    },
    "earth_aw3d30": {
        "id": "earth_aw3d30", "body": "earth", "provider": "JAXA ALOS via OpenTopography",
        "product": "ALOS World 3D 30 m (AW3D30) DSM", "native_resolution_m": 30.0,
        "access": {"method": "opentopography_globaldem",
                   "endpoint": "https://portal.opentopography.org/API/globaldem", "demtype": "AW3D30"},
        "crs": "EPSG:4326", "vertical_datum": "EGM96 (approx)",
        "key_required": True, "license": "JAXA; free use with attribution",
        "citation": "JAXA ALOS World 3D-30m (AW3D30), via OpenTopography",
        "coverage": {"kind": "global_land", "bboxes": _EARTH_GLOBAL, "complete": True,
                     "valid_resolution_range_m": [30.0, 500000.0],
                     "description": "Global land DSM (surface incl. canopy/buildings)"},
    },
}

REQUIRED_FIELDS = ("id", "body", "provider", "product", "native_resolution_m",
                   "access", "crs", "vertical_datum", "key_required", "license",
                   "citation", "coverage", "preference", "nodata_sentinels")

# Retrieval hints added post-hoc to keep the SOURCES literal readable.
#   preference: lower = better suited to cross-body LAND-SURFACE morphology screening
#     (resolution, consistency, void handling). It is a documented, honest heuristic
#     for *this* task, NOT a universal "quality" ranking of the products.
#   nodata_sentinels: extra values to drop beyond the raster's own declared nodata --
#     a safety net for undeclared voids (e.g. SRTM's -32768, ALOS's -9999). Copernicus
#     and the Mars/3DEP products rely on the raster mask, so their list is empty.
_PREFERENCE = {
    "earth_cop30": 1, "earth_usgs10m": 1, "earth_usgs1m": 1,
    "earth_cop90": 2, "earth_nasadem": 2, "earth_aw3d30": 2,
    "earth_srtmgl1": 3, "earth_srtmgl3": 3,
    "mars_mola_usgs_463m": 1, "mars_mola_megdr": 2,
    "moon_lola_ldem": 1, "mercury_messenger_dem": 1, "ceres_dawn_dem": 1,
}
_NODATA = {
    "earth_srtmgl1": [-32768.0], "earth_srtmgl3": [-32768.0],
    "earth_nasadem": [-32768.0], "earth_aw3d30": [-9999.0],
}
for _sid, _s in SOURCES.items():
    _s.setdefault("preference", _PREFERENCE.get(_sid, 5))
    _s.setdefault("nodata_sentinels", list(_NODATA.get(_sid, [])))


def all_ids():
    return sorted(SOURCES)


def get(source_id):
    if source_id not in SOURCES:
        raise KeyError(f"unknown source {source_id!r}; known: {all_ids()}")
    return SOURCES[source_id]


def by_body(body):
    return [s for s in SOURCES.values() if s["body"] == body.lower()]


def nodata_sentinels_for(source_id):
    """Extra sentinel values to drop (beyond the raster's declared nodata) for a
    source. Apply with masks.apply_masks(z, mask_values=...) right after load."""
    return list(get(source_id).get("nodata_sentinels", []))


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

    Among sources that cover the bbox for `body`, selection is:
      1. `preference` tier (lower = better suited to land-surface morphology) first,
         so e.g. Copernicus GLO-30 wins over a coarse SRTM product at the same tier
         boundary -- preference is a documented heuristic for THIS task, not a
         universal quality claim;
      2. then native resolution fine enough to aggregate UP to target_support_m
         (native <= target); within a tier the coarsest that still qualifies, to
         minimise download while meeting the support;
      3. if none qualify, the finest available, with a warning that the target
         support is finer than any covered source can provide.
    Complete-coverage sources beat advertised-but-partial ones at an equal key.
    Returns {source_id, reason, warnings, candidates}.
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
        scored.append((s["id"], float(s["native_resolution_m"]),
                       bool(cov["complete"]), int(s.get("preference", 5))))
    if not scored:
        return {"source_id": None, "reason": "no covered source for this bbox/body",
                "warnings": warnings, "candidates": []}
    qualifying = [t for t in scored if t[1] <= target_support_m]
    if qualifying:
        # preference tier, then coarsest native <= target (least download), then
        # complete-over-partial, then id for determinism.
        qualifying.sort(key=lambda t: (t[3], -t[1], not t[2], t[0]))
        best = qualifying[0]
        reason = (f"preference tier {best[3]}, native {best[1]:g} m <= target support "
                  f"{target_support_m:g} m; least-download choice that meets the support")
    else:
        scored.sort(key=lambda t: (t[1], t[3], not t[2], t[0]))
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
        if s.get("body") not in ("mars", "earth", "moon", "mercury", "ceres"):
            problems.append((sid, f"body not in known bodies: {s.get('body')!r}"))
        res = s.get("native_resolution_m")
        if not isinstance(res, (int, float)) or res <= 0:
            problems.append((sid, f"native_resolution_m not positive: {res!r}"))
        if not isinstance(s.get("key_required"), bool):
            problems.append((sid, "key_required not bool"))
        pref = s.get("preference")
        if not isinstance(pref, int) or isinstance(pref, bool) or pref < 1:
            problems.append((sid, f"preference not a positive int: {pref!r}"))
        nod = s.get("nodata_sentinels")
        if not isinstance(nod, list) or not all(isinstance(v, (int, float)) for v in nod):
            problems.append((sid, f"nodata_sentinels not a numeric list: {nod!r}"))
        if "coverage" in s:
            problems.extend(_coverage_problems(sid, s["coverage"]))
    return problems