"""Local metric (azimuthal-equidistant) reprojection to a common support.

Mars MOLA and Earth Copernicus/USGS DEMs live in different coordinate
systems on different bodies (Mars sphere R=3,396,190 m vs Earth WGS84).
Computing slope/relief in "metres" directly on a degrees grid, or sharing
one dx across bodies, is wrong because degree spacing varies with latitude
and body radius.

This module warps each AOI onto its own **local azimuthal-equidistant**
metric grid at a chosen resolution, using the correct body, and area-averages
when downsampling (so coarse support is a true average, not an aliased point
sample). Distances are true from the AOI centre; scale distorts outward, so
prefer bounded AOIs. Feature statistics are then computed on true metres.

The warp needs rasterio+GDAL (optional). The pure helpers below
(CRS strings, centroid, grid sizing) are dependency-free and unit-tested.
"""
from __future__ import annotations

import math

MARS_RADIUS_M = 3396190.0  # IAU mean radius
MOON_RADIUS_M = 1737400.0  # IAU lunar mean radius (LRO/LOLA sphere)
MERCURY_RADIUS_M = 2439400.0  # IAU Mercury mean radius (MESSENGER sphere)
CERES_RADIUS_M = 469730.0  # Dawn Ceres mean radius (near-spherical dwarf planet)

# Spherical bodies handled with an authalic-sphere proj string. Earth is the one
# ellipsoidal exception (WGS84), kept separate below. These spheres are a good
# model for the near-round bodies here; strongly irregular bodies (e.g. Vesta)
# are deliberately NOT offered, as a single sphere would misrepresent them.
_SPHERE_RADIUS_M = {
    "mars": MARS_RADIUS_M, "moon": MOON_RADIUS_M,
    "mercury": MERCURY_RADIUS_M, "ceres": CERES_RADIUS_M,
}


def body_radius_m(body):
    """Mean radius in metres for a supported body (Earth uses the WGS84 mean)."""
    b = body.lower()
    if b == "earth":
        return 6371008.8
    if b in _SPHERE_RADIUS_M:
        return _SPHERE_RADIUS_M[b]
    raise ValueError(f"unknown body {body!r}")


def geographic_crs(body):
    """Geographic (lon/lat) CRS for the body."""
    b = body.lower()
    if b == "earth":
        return "EPSG:4326"
    if b in _SPHERE_RADIUS_M:
        r = _SPHERE_RADIUS_M[b]
        return f"+proj=longlat +a={r} +b={r} +no_defs"
    raise ValueError(f"unknown body {body!r}")


def local_aeqd(lat0, lon0, body):
    """Local azimuthal-equidistant metric CRS centred on (lat0, lon0)."""
    b = body.lower()
    if b == "earth":
        return (f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
                f"+datum=WGS84 +units=m +no_defs")
    if b in _SPHERE_RADIUS_M:
        r = _SPHERE_RADIUS_M[b]
        return (f"+proj=aeqd +lat_0={lat0} +lon_0={lon0} "
                f"+a={r} +b={r} +units=m +no_defs")
    raise ValueError(f"unknown body {body!r}")


def centroid(bbox):
    """Centre (lon0, lat0) of a (west, south, east, north) degree bbox.

    Antimeridian-aware: if the box crosses +/-180 (west > east) the centre
    longitude is computed on the wrapped interval.
    """
    west, south, east, north = bbox
    lat0 = 0.5 * (south + north)
    if west <= east:
        lon0 = 0.5 * (west + east)
    else:                                   # crosses the antimeridian
        lon0 = (0.5 * (west + east + 360.0)) % 360.0
        if lon0 > 180.0:
            lon0 -= 360.0
    return (lon0, lat0)


def grid_size(xmin, ymin, xmax, ymax, resolution_m):
    """Destination grid (width, height) in pixels for a metric bbox."""
    if resolution_m <= 0:
        raise ValueError("resolution_m must be positive")
    width = max(int(math.ceil((xmax - xmin) / resolution_m)), 1)
    height = max(int(math.ceil((ymax - ymin) / resolution_m)), 1)
    return width, height


def read_aoi_metric(path, bbox_lonlat, resolution_m, body, resampling="average",
                    mask_below=None, mask_values=None, mask_above=None):
    """Read a DEM AOI and warp it to a local metric grid.

    bbox_lonlat = (west, south, east, north) in degrees on the body.
    `resampling` defaults to area-weighted "average" so downsampling to a coarse
    common support is a true average, not an aliased point sample. Optional masks
    (applied in the source CRS before warping) convert sentinels such as
    Copernicus 0 m ocean to NaN so flat water does not contaminate morphology.
    Returns (elevation_array_with_nan, resolution_m). Requires rasterio.
    """
    import numpy as np
    from . import masks as _masks
    try:
        import rasterio
        from rasterio.warp import reproject, transform_bounds, Resampling
        from affine import Affine
    except Exception as exc:  # pragma: no cover
        raise RuntimeError("pip install rasterio  (needed for reprojection)") from exc

    geo = geographic_crs(body)
    lon0, lat0 = centroid(bbox_lonlat)
    dst_crs = local_aeqd(lat0, lon0, body)
    resamp = getattr(Resampling, resampling)

    with rasterio.open(path) as ds:
        if ds.crs is None:
            raise RuntimeError(f"{path} has no CRS; cannot reproject safely")
        # 1) crop in source CRS by converting the lon/lat bbox into it.
        west, south, east, north = bbox_lonlat
        src_w, src_s, src_e, src_n = transform_bounds(geo, ds.crs, west, south, east, north)
        from rasterio.windows import from_bounds
        win = from_bounds(src_w, src_s, src_e, src_n, ds.transform)
        src = ds.read(1, window=win, boundless=True, masked=True)
        src_arr = src.astype("float64").filled(np.nan)
        src_arr = _masks.apply_masks(src_arr, mask_below=mask_below,
                                     mask_values=mask_values, mask_above=mask_above)
        src_transform = ds.window_transform(win)
        src_crs = ds.crs
        src_nodata = np.nan   # NaNs are the nodata sentinel; keep average from bleeding across them

    # 2) destination metric grid covering the AOI in the local aeqd CRS.
    from rasterio.warp import transform_bounds as _tb
    dxmin, dymin, dxmax, dymax = _tb(geo, dst_crs, *bbox_lonlat)
    width, height = grid_size(dxmin, dymin, dxmax, dymax, resolution_m)
    dst_transform = Affine(resolution_m, 0, dxmin, 0, -resolution_m, dymax)
    dst = np.full((height, width), np.nan, dtype="float64")

    reproject(
        source=src_arr, destination=dst,
        src_transform=src_transform, src_crs=src_crs,
        dst_transform=dst_transform, dst_crs=dst_crs,
        src_nodata=src_nodata, dst_nodata=np.nan,
        resampling=resamp,
    )
    return dst, float(resolution_m)
