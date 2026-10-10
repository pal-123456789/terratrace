"""Curated library of planetary reference sites and terrestrial analog sites.

A built-in registry of WELL-KNOWN places on Mars, the Moon, Mercury and Earth,
exposed as ready-to-use AOI presets so a study or batch can be assembled from
named sites (``jezero_crater``, ``craters_of_the_moon``, ...) instead of hand-
typed bounding boxes. Each entry carries a stable id, its body, a human name, an
approximate bbox and a short note; the ``to_aoi_unit`` / ``to_aoi_units`` helpers
turn those into the same unit-dict shape used by ``config/aois.example.yml`` and
``config/batch.example.yml`` (and understood by ``preflight`` / ``catalog``).

HONESTY CAVEATS (read before trusting a preset):
  * The bboxes are APPROXIMATE bounding windows drawn around published site
    centres -- convenient framing rectangles, not authoritative mission
    footprints, geologic-unit boundaries, or survey extents. Refine them to your
    DEM and science question before use.
  * The sites are ILLUSTRATIVE examples chosen to be recognisable and useful for
    cross-body morphology screening. They are NOT NASA-endorsed, and inclusion
    here implies no endorsement by NASA, USGS, ESA or any mission team.
  * The map-scale-morphology claim firewall still applies. TerraTrace compares
    land-surface shape at a common map scale; naming a site "an analog" here is a
    convenience label for that screening, NOT a geological, astrobiological or
    operational claim that the terrestrial site is equivalent to the planetary
    one. Any downstream statement must stay within the map-scale morphology
    evidence the engine actually produces.
"""
from __future__ import annotations

from . import catalog

# Approximate bounding windows (west, south, east, north) in degrees. Planetary
# longitudes are 0..360 EAST (preflight also accepts -180..180 for those bodies);
# Earth is -180..180. All values are APPROXIMATE -- see the module caveats.
REGIONS = {
    # --- Mars (reference body; windows cropped from global MOLA) --------------
    "jezero_crater": {
        "id": "jezero_crater", "body": "mars", "name": "Jezero Crater",
        "bbox": [77.2, 18.2, 77.8, 18.8],
        "note": "Perseverance landing site, delta",
    },
    "gale_crater": {
        "id": "gale_crater", "body": "mars", "name": "Gale Crater",
        "bbox": [137.2, -5.7, 138.0, -4.9],
        "note": "Curiosity landing site",
    },
    "valles_marineris": {
        "id": "valles_marineris", "body": "mars", "name": "Valles Marineris",
        "bbox": [285.0, -14.0, 295.0, -6.0],
        "note": "canyon system; large window",
    },
    # --- Moon (LRO/LOLA) ------------------------------------------------------
    "mare_tranquillitatis": {
        "id": "mare_tranquillitatis", "body": "moon", "name": "Mare Tranquillitatis",
        "bbox": [23.0, 0.3, 24.2, 1.3],
        "note": "Apollo 11 region",
    },
    "aristarchus_plateau": {
        "id": "aristarchus_plateau", "body": "moon", "name": "Aristarchus Plateau",
        "bbox": [310.0, 22.0, 313.0, 26.0],
        "note": "volcanic plateau",
    },
    # --- Mercury (MESSENGER) --------------------------------------------------
    "caloris_basin": {
        "id": "caloris_basin", "body": "mercury", "name": "Caloris Basin",
        "bbox": [160.0, 22.0, 172.0, 34.0],
        "note": "large impact basin",
    },
    # --- Earth (terrestrial analog sites) -------------------------------------
    "hawaii_mauna_loa": {
        "id": "hawaii_mauna_loa", "body": "earth", "name": "Mauna Loa, Hawaii",
        "bbox": [-155.7, 19.3, -155.4, 19.6],
        "note": "basaltic shield; Mars/Moon analog",
    },
    "iceland_highlands": {
        "id": "iceland_highlands", "body": "earth", "name": "Icelandic Highlands",
        "bbox": [-19.2, 64.7, -18.6, 65.1],
        "note": "volcanic/periglacial analog",
    },
    "atacama_desert": {
        "id": "atacama_desert", "body": "earth", "name": "Atacama Desert",
        "bbox": [-69.3, -24.2, -68.9, -23.8],
        "note": "hyperarid Mars soil/landform analog",
    },
    "devon_island": {
        "id": "devon_island", "body": "earth", "name": "Devon Island",
        "bbox": [-90.2, 75.2, -89.4, 75.6],
        "note": "Haughton impact; polar desert analog",
    },
    "craters_of_the_moon": {
        "id": "craters_of_the_moon", "body": "earth", "name": "Craters of the Moon, Idaho",
        "bbox": [-113.6, 43.3, -113.3, 43.6],
        "note": "Idaho basaltic lava field",
    },
}
_SUPPORTED_BODIES = ("mars", "earth", "moon", "mercury", "ceres")


def all_regions():
    """Sorted list of all known region ids."""
    return sorted(REGIONS)


def get(region_id):
    """Return the preset dict for `region_id`; KeyError (listing known ids) on miss."""
    if region_id not in REGIONS:
        raise KeyError(f"unknown region {region_id!r}; known: {all_regions()}")
    return REGIONS[region_id]


def by_body(body):
    """All preset dicts whose body matches `body` (case-insensitive)."""
    b = str(body).lower()
    return [r for r in REGIONS.values() if r["body"] == b]

def to_aoi_unit(region_id, path=None, is_reference=False, **extra):
    """Turn a preset into a config unit-dict (the aois/batch example shape).

    Produces id/body/bbox/name/note plus rights_status="verified_allowed",
    access_status="unknown", the is_reference flag, and a path (defaulting to
    f"data/{body}/{region_id}.tif"). Optional retrieval knobs passed in `extra`
    (native_posting_m, demtype, dataset, and any other unit keys) flow through
    without ever clobbering the canonical fields above.

    A "suggested_source" is attached from catalog.recommend_source(bbox, body,
    target_support_m=extra.get("target_support_m", 2000.0)); it names the product
    the catalog would pick for this window at that common support -- advisory,
    not a download guarantee (see the catalog/preflight caveats). The
    `target_support_m` knob drives only that suggestion and is NOT written into
    the unit. Raises KeyError for an unknown region_id.
    """
    region = get(region_id)
    body = region["body"]
    bbox = list(region["bbox"])
    target_support_m = extra.get("target_support_m", 2000.0)
    suggested = catalog.recommend_source(bbox, body, target_support_m=target_support_m)

    unit = {
        "id": region["id"],
        "body": body,
        "bbox": bbox,
        "name": region["name"],
        "note": region["note"],
        "rights_status": "verified_allowed",
        "access_status": "unknown",
        "is_reference": bool(is_reference),
        "path": path if path is not None else f"data/{body}/{region_id}.tif",
        "suggested_source": suggested["source_id"],
    }
    # Forward any caller-supplied knobs (native_posting_m, demtype, dataset, ...)
    # but never the control-only target_support_m, and never overwrite a canonical
    # field (so bbox/body stay consistent with the computed suggested_source).
    for key, val in extra.items():
        if key == "target_support_m":
            continue
        unit.setdefault(key, val)
    return unit

def to_aoi_units(region_ids, reference_id=None, **common):
    """Map several region ids to unit-dicts (see `to_aoi_unit`).

    `reference_id`, if given, is the one id marked is_reference=True (typically a
    planetary reference window); every other unit is is_reference=False. `common`
    keyword knobs (e.g. target_support_m, native_posting_m) are forwarded to each
    `to_aoi_unit`. Raises KeyError if any region_id is unknown.
    """
    return [to_aoi_unit(rid, is_reference=(rid == reference_id), **common)
            for rid in region_ids]


def validate():
    """Return a list of (id, problem) for any malformed preset; empty == clean.

    Mirrors catalog.validate(): checks each entry's id matches its key, the body
    is known, name/note are non-empty strings, and the bbox passes the engine's
    own preflight.validate_bbox for that body (so a bad preset is caught here,
    not only when a user tries to run it).
    """
    from . import preflight            # local import: avoids an unused dependency
    problems = []
    for rid, r in REGIONS.items():
        if r.get("id") != rid:
            problems.append((rid, "id field mismatch"))
        if r.get("body") not in _SUPPORTED_BODIES:
            problems.append((rid, f"body not in known bodies: {r.get('body')!r}"))
        for field in ("name", "note"):
            if not (isinstance(r.get(field), str) and r.get(field)):
                problems.append((rid, f"missing or empty {field}"))
        for m in preflight.validate_bbox(r.get("bbox"), r.get("body")):
            problems.append((rid, m))
    return problems
