"""Source-lock records for reproducibility and citation.

Pure helpers (hashing, citation text) are dependency-free and tested.
Geospatial enrichment (CRS/bounds/shape) is added by the companion script
using rasterio on the machine that holds the DEM files.
"""
from __future__ import annotations

import hashlib
import os

CITATIONS = {
    "mars": ("Smith, D. E., et al. Mars Global Surveyor MOLA Mission Experiment "
             "Gridded Data Record (MEGDR); USGS Astrogeology 'Mars MGS MOLA DEM 463m'. "
             "NASA PDS Geosciences Node."),
    "earth": ("ESA Copernicus GLO-30 Digital Elevation Model, distributed by "
              "OpenTopography. (c) ESA. Attribution required."),
}

TERMS = {
    "mars": "NASA PDS / USGS public data; attribution required; cite product + version.",
    "earth": "Copernicus data; free use with attribution; see OpenTopography terms.",
}


def sha256_file(path, chunk=1 << 20):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def citation_for(body):
    b = body.lower()
    if b not in CITATIONS:
        raise ValueError(f"no citation for body {body!r}")
    return CITATIONS[b]


def terms_for(body):
    b = body.lower()
    if b not in TERMS:
        raise ValueError(f"no terms for body {body!r}")
    return TERMS[b]


def build_entry(unit, geo=None):
    """Build one source-lock entry for a config unit dict.

    geo: optional dict of geospatial metadata (crs, bounds, shape, nodata).
    """
    path = unit["path"]
    body = unit.get("body", "earth")
    entry = {
        "id": unit["id"],
        "path": path,
        "body": body,
        "exists": os.path.exists(path),
        "sha256": sha256_file(path) if os.path.exists(path) else None,
        "bytes": os.path.getsize(path) if os.path.exists(path) else None,
        "native_posting_m": unit.get("native_posting_m"),
        "rights_status": unit.get("rights_status", "unknown"),
        "access_status": unit.get("access_status", "unknown"),
        "citation": citation_for(body),
        "terms": terms_for(body),
    }
    if geo:
        entry["geo"] = geo
    return entry
