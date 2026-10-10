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
import random
import time

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

# Transport-error classes we retry on. Referenced defensively so the module
# still imports when `requests` is absent (then they fall back to Exception,
# which the pure-NumPy test path never triggers); when `requests` is installed
# these are the real exception classes, so a fail-fast RuntimeError is never
# mistaken for a transient transport error.
_ReqConnErr = getattr(getattr(requests, "exceptions", None), "ConnectionError", Exception)
_ReqTimeout = getattr(getattr(requests, "exceptions", None), "Timeout", Exception)

# HTTP statuses worth retrying: 429 (rate limit, e.g. OpenTopography) plus the
# common 5xx gateway/overload codes servers emit transiently under load.
_TRANSIENT_STATUSES = frozenset({429, 500, 502, 503, 504})

OPENTOPO_GLOBALDEM = "https://portal.opentopography.org/API/globaldem"
OPENTOPO_USGSDEM = "https://portal.opentopography.org/API/usgsdem"
TNM_3DEP_IMAGESERVER = ("https://elevation.nationalmap.gov/arcgis/rest/services/"
                        "3DEPElevation/ImageServer/exportImage")


def _require_requests():
    if requests is None:
        raise RuntimeError("pip install requests  (needed for downloads)")


def _require_rasterio():
    if rasterio is None:
        raise RuntimeError("pip install rasterio  (needed to read DEM rasters)")


def _stream(url, params, out_path, retries=4, backoff=1.0, max_sleep=60.0,
            timeout=600, session=None):
    """Stream a GET to out_path atomically, retrying transient failures.

    Writes to ``out_path + ".part"`` and ``os.replace``s it into place only on a
    2xx response, so a caller never sees a truncated file; the partial file is
    removed after every failed attempt and on final give-up.

    Up to ``retries`` retries (``retries + 1`` attempts total) are made on HTTP
    429/500/502/503/504 and on ``requests`` ConnectionError/Timeout, with bounded
    exponential backoff. A numeric ``Retry-After`` header is honored (sleep that
    many seconds, capped at ``max_sleep``); otherwise the sleep is
    ``min(max_sleep, backoff * 2**attempt)`` plus a small random jitter in
    ``[0, backoff)``. Permanent errors (any other status >= 400, e.g. a 4xx
    other than 429) fail fast with a RuntimeError carrying the status and a
    snippet of the response body - no retry. Exhausting all attempts raises a
    RuntimeError summarizing the last transient status/exception.

    ``session`` injects a ``requests``-like object (used by tests to avoid the
    network); when it is None the real ``requests`` module is required and used.
    """
    sess = session or requests
    if session is None:
        _require_requests()
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    tmp = out_path + ".part"

    def _sleep_for(retry_after, attempt):
        if retry_after is not None:
            try:
                return min(max_sleep, max(0.0, float(str(retry_after).strip())))
            except (TypeError, ValueError):
                pass
        base = min(max_sleep, backoff * (2 ** attempt))
        return base + (random.random() * backoff if backoff > 0 else 0.0)

    transient_status = None
    transient_exc = None
    transient_body = ""
    try:
        for attempt in range(retries + 1):
            transient_status = None
            transient_exc = None
            retry_after = None
            fatal = None
            try:
                with sess.get(url, params=params, stream=True, timeout=timeout) as r:
                    status = getattr(r, "status_code", None)
                    if status in _TRANSIENT_STATUSES:
                        transient_status = status
                        try:
                            retry_after = r.headers.get("Retry-After")
                        except Exception:
                            retry_after = None
                        try:
                            transient_body = (r.text or "")[:200]
                        except Exception:
                            transient_body = ""
                    elif status is not None and status >= 400:
                        try:
                            body = (r.text or "")[:200]
                        except Exception:
                            body = ""
                        fatal = (status, body)
                    else:
                        with open(tmp, "wb") as fh:
                            for chunk in r.iter_content(chunk_size=1 << 20):
                                if chunk:
                                    fh.write(chunk)
                        os.replace(tmp, out_path)
                        return out_path
            except (_ReqConnErr, _ReqTimeout) as exc:
                transient_exc = exc

            # Drop any partial .part written before this attempt failed.
            if os.path.exists(tmp):
                os.remove(tmp)

            # Permanent error -> fail fast (outside the transport except so the
            # RuntimeError is never swallowed as a transient error).
            if fatal is not None:
                raise RuntimeError(
                    f"download failed: HTTP {fatal[0]} from {url} "
                    f"(permanent client/server error, no retry): {fatal[1]}")

            if attempt >= retries:
                break
            time.sleep(_sleep_for(retry_after, attempt))
        if transient_exc is not None:
            reason = f"{type(transient_exc).__name__}: {transient_exc}"
        else:
            reason = f"HTTP {transient_status}"
            if transient_body:
                reason += f" ({transient_body})"
        raise RuntimeError(
            f"download failed after {retries + 1} attempt(s) from {url} "
            f"(last transient error: {reason})")
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def fetch_opentopo_global(bbox, api_key, out_path, demtype="COP30"):
    """Download a global DEM (COP30/COP90/SRTMGL1/NASADEM/AW3D30/...) from the
    OpenTopography globaldem API. bbox = (west, south, east, north) in degrees."""
    west, south, east, north = bbox
    return _stream(OPENTOPO_GLOBALDEM,
                   {"demtype": demtype, "west": west, "south": south, "east": east,
                    "north": north, "outputFormat": "GTiff", "API_Key": api_key}, out_path)


def fetch_copernicus_glo30(bbox, api_key, out_path, demtype="COP30"):
    """Copernicus GLO-30/90 via OpenTopography (thin wrapper over the global API)."""
    return fetch_opentopo_global(bbox, api_key, out_path, demtype=demtype)


def fetch_usgs_3dep(bbox, api_key, out_path, dataset="USGS10m"):
    """USGS 3DEP seamless DEM via the OpenTopography usgsdem API (reuses the same
    free key). dataset in {USGS30m, USGS10m, USGS1m}; USGS1m may require enabled
    academic access. bbox = (west, south, east, north) in degrees."""
    west, south, east, north = bbox
    return _stream(OPENTOPO_USGSDEM,
                   {"datasetName": dataset, "west": west, "south": south, "east": east,
                    "north": north, "outputFormat": "GTiff", "API_Key": api_key}, out_path)


def _is_tiff(path):
    """True if the file starts with a TIFF magic header (II* little- or MM* big-endian).
    The 3DEP ImageServer returns error responses as HTTP 200 + JSON, so a byte check
    is the only reliable way to tell a real GeoTIFF from an error payload."""
    with open(path, "rb") as fh:
        return fh.read(2) in (b"II", b"MM")


def fetch_3dep_imageserver(bbox, out_path, size=(1024, 1024)):
    """Keyless 3DEP fallback: the USGS 3DEPElevation ImageServer returns a
    bbox-clipped GeoTIFF in one request. bbox = (west, south, east, north) deg."""
    west, south, east, north = bbox
    sx, sy = size
    _stream(TNM_3DEP_IMAGESERVER,
            {"bbox": f"{west},{south},{east},{north}", "bboxSR": 4326,
             "size": f"{sx},{sy}", "format": "tiff", "pixelType": "F32",
             "f": "image"}, out_path)
    # ImageServer returns errors as HTTP 200 + JSON; reject anything not a TIFF.
    if not _is_tiff(out_path):
        os.remove(out_path)
        raise RuntimeError("3DEP ImageServer did not return a GeoTIFF (likely an error "
                           "response); check the bbox is within US 3DEP coverage.")
    return out_path


def download(url, out_path):
    """Generic atomic download helper (e.g. a staged 3DEP COG or MOLA GeoTIFF URL)."""
    return _stream(url, None, out_path)


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
    """Read only a bounding-box window (west,south,east,north) in the raster CRS.

    Returns (elevation_array_with_nan, native_posting_m). Posting is in metres;
    for a geographic (degree) CRS it is approximated at the window's central
    latitude, mirroring load_dem_array so callers get a consistent support unit.
    """
    _require_rasterio()
    from rasterio.windows import from_bounds
    with rasterio.open(path) as ds:
        west, south, east, north = bbox
        win = from_bounds(west, south, east, north, ds.transform)
        z = ds.read(1, window=win, masked=True).astype("float64").filled(np.nan)
        a = abs(ds.transform.a)
        crs = ds.crs
        if crs and crs.is_geographic:
            lat = (south + north) / 2.0
            posting_m = a * 111320.0 * max(math.cos(math.radians(lat)), 1e-6)
        else:
            posting_m = a  # projected CRS already in metres (MOLA, UTM, etc.)
    return z, float(posting_m)
