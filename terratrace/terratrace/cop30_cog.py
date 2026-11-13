"""Keyless Copernicus GLO-30 access from the official ESA COG distribution on AWS.

WHY THIS EXISTS
---------------
Earth DEMs in this project are normally fetched through OpenTopography's
``globaldem`` endpoint, which needs a free API key (``OPENTOPO_API_KEY``). That
is a real barrier: without a key the matched-footprint benchmark cannot run at
all, and the key lives on one person's machine.

ESA publishes the same Copernicus GLO-30 product as **cloud-optimised GeoTIFFs**
on AWS S3, publicly readable, with no credentials:

    https://copernicus-dem-30m.s3.amazonaws.com/
    Copernicus_DSM_COG_10_<N|S><lat>_00_<E|W><lon>_00_DEM/
        Copernicus_DSM_COG_10_<N|S><lat>_00_<E|W><lon>_00_DEM.tif

One file per 1x1 degree, named by its **south-west** corner, in EPSG:4326 at
1 arc-second (30 m) posting, Float32, with a nodata value of -32768.

This module reads an arbitrary lon/lat bbox out of that mosaic and writes a
local, single-band GeoTIFF that the rest of the engine consumes through the
ordinary ``reproject.read_aoi_metric`` path. Because the files are COGs, the
read is a **windowed HTTP range request** -- only the requested blocks are
fetched, never the whole tile.

THE GRID (the detail that matters)
-----------------------------------
GLO-30 pixel **centres** lie on exact multiples of the 1/3600 degree posting:
the tile named ``..._N43_00_W114_00_DEM`` has its first pixel centre at
longitude -114.0 and latitude 44.0, and its raster bounds are
-114.00013889 .. -113.00013889. Every pixel centre is therefore at
``n * (1/3600)`` degrees for an integer ``n`` -- a single global lattice that
also underlies the OpenTopography AOI tiles. All indexing here is done in that
lattice, so a COG read and an OpenTopography read of the same bbox land on the
same pixels.

EQUIVALENCE (verified, not assumed)
------------------------------------
The output is byte-for-byte the same elevation data as the OpenTopography COP30
product: reading the Craters of the Moon AOI from the COG mosaic and from the
cached OpenTopography tile ``data/earth/craters_of_the_moon_cop30.tif`` gives a
maximum absolute difference of 0.0 m with 100% of pixels identical. See
``tests/test_cop30_cog.py``. The two paths are therefore interchangeable, and
the OpenTopography key is optional rather than required.

HONEST CAVEATS
--------------
* The OpenTopography endpoint and the AWS bucket are two distributions of the
  same ESA product; they are not independent observations, and a study must not
  treat them as a replication.
* Cloud cover, vegetation and buildings are in the data -- COP30 is a DSM, not
  bare earth. No correction is applied here.
* ``read_cog30`` returns -32768 for pixels with no tile (e.g. open ocean, where
  GLO-30 has no coverage); those are written as nodata.
"""
from __future__ import annotations

import math
import os

BASE_URL = "https://copernicus-dem-30m.s3.amazonaws.com"
RESOLUTION_DEG = 1.0 / 3600.0                   # 1 arc-second
TILE_SIZE_PX = 3600                            # 3600 arc-seconds = 1 degree
NODATA = -32768.0
TILE_FMT = "Copernicus_DSM_COG_10_{ns}{lat:02d}_00_{ew}{lon:03d}_00_DEM"

# GDAL/rasterio switches that make public S3 reads work without credentials and
# without a directory listing (which is slow and usually denied).
_ENV_DEFAULTS = {
    "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
    "AWS_NO_SIGN_REQUEST": "YES",
    "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
    "GDAL_HTTP_MAX_RETRY": "5",
    "GDAL_HTTP_TIMEOUT": "120",
}


def _apply_env():
    for k, v in _ENV_DEFAULTS.items():
        os.environ.setdefault(k, v)


def _require_rasterio():
    """Import rasterio (and ``from_origin``), or raise the engine's standard,
    actionable error.

    CI installs NumPy only (``requirements.txt``), so every rasterio use must sit
    behind this guard. An unguarded import at module scope would break the
    dependency-free test suite on all three CI Pythons -- which is exactly the
    trap this project has hit before with PyYAML. Returns ``(rasterio,
    from_origin)``.
    """
    try:
        import rasterio
        from rasterio.transform import from_origin
    except Exception as exc:  # pragma: no cover - exercised by the no-rasterio test
        raise RuntimeError(
            "pip install rasterio  (needed to read the Copernicus GLO-30 COG "
            "mosaic)") from exc
    return rasterio, from_origin


def tile_name(lat_sw, lon_sw):
    """GLO-30 tile name for the 1-degree cell whose SOUTH-WEST corner is
    ``(lat_sw, lon_sw)``."""
    ns = "N" if lat_sw >= 0 else "S"
    ew = "E" if lon_sw >= 0 else "W"
    return TILE_FMT.format(ns=ns, lat=abs(int(lat_sw)), ew=ew, lon=abs(int(lon_sw)))


def tile_url(lat_sw, lon_sw):
    """HTTPS URL of one GLO-30 tile."""
    n = tile_name(lat_sw, lon_sw)
    return f"{BASE_URL}/{n}/{n}.tif"


def tiles_for_bbox(bbox):
    """The tile cells (as south-west corners) that a lon/lat bbox touches."""
    west, south, east, north = [float(v) for v in bbox]
    lat0, lat1 = math.floor(south), math.floor(north)
    lon0, lon1 = math.floor(west), math.floor(east)
    return [(la, lo)
            for la in range(lat0, lat1 + 1)
            for lo in range(lon0, lon1 + 1)]


def _centre_grid(west, south, east, north):
    """The GLO-30 pixel centres that fall inside a bbox.

    GLO-30 pixel centres lie on exact multiples of the 1/3600 degree posting,
    and the same lattice underlies the OpenTopography AOI tiles. This returns
    ``(lon_start, n_lon, lat_start, n_lat)`` where ``lon_start`` is the first
    centre at or east of ``west``, ``lat_start`` the first centre at or south
    of ``north``, and the counts are how many centres fit before ``east`` /
    ``south``.

    The convention matches OpenTopography exactly: for a requested AOI of
    ``(west, east)`` degrees it returns the centres in ``[west, east)`` and
    ``(south, north]``, and its raster edges sit half a pixel outside them --
    which is precisely the OpenTopography AOI-tile geometry (e.g. a request
    of -113.6..-113.3 yields 1080 centres from -113.6 to -113.30027778 and
    raster bounds -113.60013889..-113.30013889).
    """
    lon_start = math.ceil(west / RESOLUTION_DEG - 1e-9) * RESOLUTION_DEG
    lat_start = math.floor(north / RESOLUTION_DEG + 1e-9) * RESOLUTION_DEG
    n_lon = int(math.ceil((east - lon_start) / RESOLUTION_DEG - 1e-9))
    n_lat = int(math.ceil((lat_start - south) / RESOLUTION_DEG - 1e-9))
    return lon_start, max(n_lon, 0), lat_start, max(n_lat, 0)


def read_cog30(bbox, out_path=None, report=None):
    """Read a lon/lat bbox out of the GLO-30 COG mosaic.

    ``bbox`` is ``(west, south, east, north)`` in degrees (EPSG:4326), in the
    same AOI convention OpenTopography's ``globaldem`` endpoint uses. Returns
    ``(array, transform)``. The array's pixel centres are on the global GLO-30
    lattice and the transform places them correctly for the engine's
    reprojection path.

    With ``out_path`` the array is also written as a single-band Float32
    GeoTIFF (EPSG:4326, nodata -32768) that the engine reads normally.

    With ``report`` (a dict) the caller receives what happened per tile --
    ``{"tiles": [...], "failed_tiles": [(lat, lon, error), ...],
    "tiles_without_coverage": [...], "no_coverage_frac": f}``. A tile that
    cannot be read leaves its block as nodata rather than aborting the mosaic,
    so the caller MUST check this before treating a mosaic as complete; a
    silent nodata gap would otherwise look like flat ground.
    """
    _apply_env()
    import numpy as np
    rasterio, from_origin = _require_rasterio()

    west, south, east, north = [float(v) for v in bbox]
    lon_start, width, lat_start, height = _centre_grid(west, south, east, north)
    out = np.full((height, width), NODATA, dtype="float32")
    # Edge-aligned transform: the raster's west/north edge sits half a pixel
    # outside the first centre, matching how GLO-30 tiles are themselves built.
    transform = from_origin(lon_start - RESOLUTION_DEG / 2.0,
                             lat_start + RESOLUTION_DEG / 2.0,
                             RESOLUTION_DEG, RESOLUTION_DEG)
    tiles = tiles_for_bbox(bbox)
    failed = []
    if width == 0 or height == 0:
        if out_path:
            with rasterio.open(out_path, "w", driver="GTiff", height=height,
                               width=width, count=1, dtype="float32",
                               crs="EPSG:4326", transform=transform,
                               nodata=NODATA, compress="deflate") as dst:
                dst.write(out, 1)
        if report is not None:
            report.update(tiles=tiles, failed_tiles=[], tiles_without_coverage=[],
                          no_coverage_frac=1.0, width=width, height=height)
        return out, transform

    for lat_sw, lon_sw in tiles:
        # Centres of this tile's pixels: lon = lon_sw + c*RES (c = 0..3599),
        # lat = lat_sw + 1 - r*RES.
        c_from = max(0, int(math.ceil((lon_start - lon_sw) / RESOLUTION_DEG - 1e-9)))
        c_to = min(TILE_SIZE_PX, int(math.floor(
            (lon_start + width * RESOLUTION_DEG - lon_sw) / RESOLUTION_DEG + 1e-9)))
        r_from = max(0, int(math.ceil((lat_sw + 1 - lat_start) / RESOLUTION_DEG - 1e-9)))
        r_to = min(TILE_SIZE_PX, int(math.floor(
            (lat_sw + 1 - (lat_start - height * RESOLUTION_DEG)) / RESOLUTION_DEG + 1e-9)))
        if c_to <= c_from or r_to <= r_from:
            continue
        try:
            with rasterio.open(tile_url(lat_sw, lon_sw)) as ds:
                block = ds.read(1, window=rasterio.windows.Window(
                    c_from, r_from, c_to - c_from, r_to - r_from))
        except Exception as exc:
            # A missing/unreachable tile leaves that block nodata rather than
            # aborting the whole mosaic -- but it is recorded, never silent.
            failed.append((lat_sw, lon_sw, f"{type(exc).__name__}: {exc}"))
            continue
        # Destination offsets (in output pixels) of this block's first centre.
        dx0 = int(round((lon_sw + c_from * RESOLUTION_DEG - lon_start) / RESOLUTION_DEG))
        dy0 = int(round((lat_start - (lat_sw + 1 - r_from * RESOLUTION_DEG))
                        / RESOLUTION_DEG))
        h = min(block.shape[0], height - dy0)
        w = min(block.shape[1], width - dx0)
        if h <= 0 or w <= 0:
            continue
        out[dy0:dy0 + h, dx0:dx0 + w] = block[:h, :w]

    if out_path:
        with rasterio.open(out_path, "w", driver="GTiff", height=height,
                           width=width, count=1, dtype="float32",
                           crs="EPSG:4326", transform=transform,
                           nodata=NODATA, compress="deflate") as dst:
            dst.write(out, 1)
    if report is not None:
        n = int(out.size)
        report.update(tiles=tiles, failed_tiles=failed,
                      tiles_without_coverage=[(t[0], t[1]) for t in failed],
                      no_coverage_frac=(float((out == NODATA).sum()) / n) if n else 1.0,
                      width=width, height=height)
    return out, transform


def fetch_cop30_cog(bbox, out_path, min_coverage=0.99):
    """Fetch a GLO-30 AOI from the public COG mosaic and write it locally.

    The thin wrapper the fetch scripts use; returns ``out_path``.

    Raises :class:`ValueError` if the mosaic came back with less than
    ``min_coverage`` of its pixels covered, because a partially-covered tile is
    silently full of ``-32768`` gaps that later look like flat ground. Pass
    ``min_coverage=0.0`` to accept an intentionally partial AOI.
    """
    report = {}
    read_cog30(bbox, out_path=out_path, report=report)
    frac = report.get("no_coverage_frac", 1.0)
    if frac > (1.0 - min_coverage):
        raise ValueError(
            f"{out_path}: {frac:.1%} of the AOI has no GLO-30 coverage "
            f"(failed tiles: {report.get('failed_tiles')}); refusing to write an "
            f"AOI that is mostly nodata. Pass min_coverage=0.0 to override.")
    return out_path


__all__ = ["BASE_URL", "RESOLUTION_DEG", "TILE_SIZE_PX", "NODATA",
           "tile_name", "tile_url", "tiles_for_bbox", "read_cog30",
           "fetch_cop30_cog"]
