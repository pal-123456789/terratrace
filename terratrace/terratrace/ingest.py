"""Real DEM ingestion for Mars (MOLA) and Earth (Copernicus / USGS 3DEP).

Network downloads and raster reads require `requests` and `rasterio`
(which bundles GDAL). These are optional so the pure-NumPy engine and its
tests run without them. Run ingestion on a machine with internet access;
the TerraTrace sandbox has no outbound network.

Minimal real stack and the only key you must create:
* Mars  - USGS Astrogeology "Mars MGS MOLA DEM 463m" GeoTIFF (no key).
* Earth - Copernicus GLO-30 via OpenTopography API (free API key).
"""
from __future__ import annotations

import math
import os

try:
    import rasterio
    import numpy as np
except Exception:  # pragma: no cover - exercised only without the extra
    rasterio = None
    import numpy as np

try:
    import requests
except Exception:  # pragma: no cover
    requests = None

OPENTOPO_GLOBALDEM = "https://portal.opentopography.org/API/globaldem"


def _require_requests():
    if requests is None:
        raise RuntimeError("pip install requests  (needed for downloads)")


def _require_rasterio():
    if rasterio is None:
        raise RuntimeError("pip install rasterio  (needed to read DEM rasters)")


def fetch_copernicus_glo30(bbox, api_key, out_path, demtype="COP30"):
    """Download a Copernicus GLO-30 (or GLO-90) GeoTIFF from OpenTopography.

    bbox = (west, south, east, north) in degrees. Returns out_path.
    Get a free key at https://portal.opentopography.org (My Account).
    """
    _require_requests()
    west, south, east, north = bbox
    params = {"demtype": demtype, "west": west, "south": south, "east": east,
              "north": north, "outputFormat": "GTiff", "API_Key": api_key}
    with requests.get(OPENTOPO_GLOBALDEM, params=params, stream=True, timeout=300) as r:
        r.raise_for_status()
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return out_path


def download(url, out_path):
    """Generic download helper (e.g. a USGS 3DEP COG or a MOLA GeoTIFF URL)."""
    _require_requests()
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
        with open(out_path, "wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
    return out_path


def load_dem_array(path):
    """Read a DEM into (elevation_float_array_with_nan, native_posting_m).

    Posting is reported in metres. For a geographic (degree) CRS it is
    approximated at the dataset's central latitude.
    """
    _require_rasterio()
    with rasterio.open(path) as ds:
        z = ds.read(1, masked=True).astype("float64").filled(np.nan)
        a = abs(ds.transform.a)
        crs = ds.crs
        if crs and crs.is_geographic:
            lat = (ds.bounds.top + ds.bounds.bottom) / 2.0
            posting_m = a * 111320.0 * max(math.cos(math.radians(lat)), 1e-6)
        else:
            posting_m = a  # projected CRS already in metres (MOLA, UTM, etc.)
    return z, float(posting_m)


def window_from_bbox(path, bbox):
    """Read only a bounding-box window (west,south,east,north) in the raster CRS."""
    _require_rasterio()
    from rasterio.windows import from_bounds
    with rasterio.open(path) as ds:
        west, south, east, north = bbox
        win = from_bounds(west, south, east, north, ds.transform)
        z = ds.read(1, window=win, masked=True).astype("float64").filled(np.nan)
        a = abs(ds.transform.a)
    return z, float(a)
