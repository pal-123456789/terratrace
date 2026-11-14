"""One exact common grid, so every unit in a comparison covers the same ground.

WHY THIS MODULE EXISTS
----------------------
The first lunar panel (`scripts/lunar_sites_demo.py`) claimed "exact common support and matched
footprint" and did not have it. Two independent errors, both measured rather than argued:

1. **Support.** Each side aggregated by its own integer factor, so a requested 500 m became 500 m
   on the Moon (5 m posting, factor 100) and **510 m** on Earth (30 m posting, factor 17). At
   1000 m it became 1000 m and **990 m** (factor 33). Only 750 m agreed, by luck.
2. **Footprint.** `centre_square()` cropped to `min(n, h, w)`, so a requested 32 x 32 grid became
   **31 x 31** on the Earth side — silently — while the written record still said
   `cells=[32, 32], support_m=500.0`. The comparison therefore ran on 16.000 km of Moon against
   15.810 km of Earth.

That is the same failure class this project already withdrew a Mars claim over: a comparison whose
footprint does not match, reported as though it did. It is a defect in the *comparison*, not in the
terrain, so no amount of descriptor care fixes it.

THE INVARIANTS, ALL MECHANICAL
------------------------------
1. **Support is ground metres on every body, by construction** — not by copying a number. The
   destination grid is built in the body's local azimuthal-equidistant CRS, whose defining property
   (validated in `scripts/reproject_analytic_check.py`) is that the distance from the projection
   centre to any projected point IS the geodesic distance on the body. So a 500 m cell is 500 m of
   ground on the Moon and on Earth.
2. **Both sides go through the same warp**, from the *native source* straight into the exact
   destination grid with area-weighted resampling. There is no intermediate grid and no per-body
   integer factor, which is what made the two sides differ in the first place.
3. **The footprint is exactly ``n * support``**, identical on both sides, and recorded.
4. **Nothing is silently resized.** If the array shape is not ``(n, n)`` this raises. Coverage is
   measured and reported, never clipped to fit.

WHY THE MOON NEEDS THE WARP TOO
-------------------------------
The LOLA products are **polar stereographic** from the south pole, so their map-north points at the
pole and a local ground grid centred on a site is **rotated** relative to the tile. Two consequences,
both measured:

* a "500 m" cell in that projection is up to **500.80 m of ground** at Site20 (the scale factor
  ``k = 1/cos^2(theta/2)`` grows with distance from the pole). Aggregating in the source projection
  would therefore compare 500.80 m lunar cells against 500.00 m terrestrial ones;
* a square window centred on the tile centre and rotated relative to it has corners at
  ``half_side * sqrt(2)`` from the centre, so a 15 km footprint does **not** fit inside the 16 km
  tiles — the largest that fits, with warp margin, is 11.27 km.

Hence the default footprint is **9000 m**: the largest value that (a) fits every site, (b) leaves
margin for the warp, and (c) is divisible by all three supports, giving exactly 18 x 18, 12 x 12 and
9 x 9 cells at exactly 500, 750 and 1000 m.
"""
from __future__ import annotations

import math

import numpy as np

from . import reproject

DEFAULT_FOOTPRINT_M = 9000.0


class ComparabilityError(RuntimeError):
    """A comparison that cannot be made on equal ground. Raised, never worked around."""


def plan(footprint_m, support_m):
    """Cells per side for an exact grid: ``footprint_m / support_m`` must be a whole number.

    An inexact plan is a comparison between different ground areas. Refusing is the whole point.
    """
    if support_m <= 0 or footprint_m <= 0:
        raise ComparabilityError(f"support and footprint must be positive, got {support_m}, {footprint_m}")
    n = footprint_m / support_m
    if abs(n - round(n)) > 1e-9:
        raise ComparabilityError(
            f"a {footprint_m} m footprint is not a whole number of {support_m} m cells "
            f"({n:.6f}); the two sides of the comparison would not cover the same ground")
    return int(round(n))


def destination_grid(lat, lon, body, support_m, n_cells):
    """The exact destination grid: ``n_cells`` x ``n_cells`` cells of ``support_m`` ground metres.

    Centred on the projection centre, so the window centre is the projection origin and every cell
    is ``support_m`` of ground from its neighbours in the local east/north frame. Returns
    ``(crs, transform, half_side_m)``.
    """
    from affine import Affine
    crs = reproject.local_aeqd(lat, lon, body)
    half = n_cells * support_m / 2.0
    transform = Affine(support_m, 0.0, -half, 0.0, -support_m, half)
    return crs, transform, half


def effective_floor_m(body, source_posting_m, factor=3.0):
    """The coarsest support a source can honestly be compared at, per this project's rule."""
    return factor * float(source_posting_m)


def read_exact(path, lat, lon, body, support_m, n_cells, resampling="average",
               mask_below=None, mask_values=None, mask_above=None, source_posting_m=None):
    """Warp a source DEM into the exact destination grid. Returns ``(array, record)``.

    Reads from the *native* source straight into the destination grid with area-weighted
    resampling, so a non-integer posting ratio (30 m -> 500 m) is a true area average rather than a
    point sample or a silently different cell size.

    ``record`` carries everything a reader needs to check the comparison without re-running it:
    the requested and achieved support, the physical footprint, the source posting, both CRSs, the
    resampling method, the valid-data fraction and the number of partially covered cells.

    Raises ``ComparabilityError`` if the grid that came back is not ``(n_cells, n_cells)`` — the
    failure that used to be silent.
    """
    try:
        import rasterio
        from rasterio.warp import reproject as _reproject, transform as _transform, Resampling
        from rasterio.windows import from_bounds
    except Exception as exc:                                     # pragma: no cover
        raise RuntimeError("pip install rasterio  (needed for a common metric grid)") from exc

    from . import masks as _masks

    dst_crs, dst_transform, half = destination_grid(lat, lon, body, support_m, n_cells)
    resamp = getattr(Resampling, resampling)

    with rasterio.open(path) as ds:
        if ds.crs is None:
            raise ComparabilityError(f"{path} has no CRS, so ground distance is undefined")
        src_crs = ds.crs
        # A posting is only a distance when the CRS is projected. A geographic CRS reports it in
        # DEGREES, and reading 0.000277 as "0.000277 m" makes the 3x source floor ~0 m, which
        # silently switches the resolution gate off -- the same shape of silent-defect this module
        # exists to remove. So a geographic source must be told its metric posting.
        if source_posting_m is not None:
            posting = float(source_posting_m)
        elif src_crs.is_geographic:
            raise ComparabilityError(
                f"{path} is geographic, so its pixel size is in degrees and not a metric posting. "
                f"Pass source_posting_m (the product's native resolution in metres) so the "
                f"resolution floor is real.")
        else:
            posting = float(ds.res[0])
        # destination corners -> source CRS, then read generously so the warp never runs off the edge
        corners_x = [-half, half, -half, half]
        corners_y = [-half, -half, half, half]
        sx, sy = _transform(dst_crs, src_crs, corners_x, corners_y)
        win = from_bounds(min(sx), min(sy), max(sx), max(sy), ds.transform)
        src_arr = ds.read(1, window=win, boundless=True, masked=True).astype("float64").filled(np.nan)
        src_arr = _masks.apply_masks(src_arr, mask_below=mask_below,
                                     mask_values=mask_values, mask_above=mask_above)
        src_transform = ds.window_transform(win)

    dst = np.full((n_cells, n_cells), np.nan, dtype="float64")
    _reproject(source=src_arr, destination=dst,
               src_transform=src_transform, src_crs=src_crs,
               dst_transform=dst_transform, dst_crs=dst_crs,
               src_nodata=np.nan, dst_nodata=np.nan, resampling=resamp)

    if dst.shape != (n_cells, n_cells):
        raise ComparabilityError(
            f"the destination came back {dst.shape}, not {(n_cells, n_cells)}. This is the defect "
            f"that used to be silent: the array was cropped to fit and the record still claimed the "
            f"requested grid.")

    # achieved support, measured off the transform rather than assumed from the argument
    ach_x, ach_y = abs(dst_transform.a), abs(dst_transform.e)
    if abs(ach_x - support_m) > 1e-9 or abs(ach_y - support_m) > 1e-9:
        raise ComparabilityError(
            f"requested {support_m} m cells, the transform describes {ach_x} x {ach_y} m")

    valid = np.isfinite(dst)
    n_valid = int(valid.sum())
    # fraction of each cell's nominal area that actually carried data, 0..1
    cover = valid.mean(axis=1) if n_cells else np.array([])
    record = {
        "cells": [n_cells, n_cells],
        "support_m_requested": float(support_m),
        "support_m_achieved": [float(ach_x), float(ach_y)],
        "footprint_m": [n_cells * float(support_m), n_cells * float(support_m)],
        "origin_lonlat": [float(lon), float(lat)],
        "source_posting_m": posting,
        "source_floor_m": effective_floor_m(body, posting),
        "source_crs": src_crs.to_string(),
        "destination_crs": str(dst_crs),
        "resampling": resampling,
        "valid_fraction": float(valid.mean()),
        "n_valid_cells": n_valid,
        "n_cells": int(dst.size),
        "n_empty_cells": int(dst.size - n_valid),
        "exact": True,
        "coverage_per_row_min": float(cover.min()) if cover.size else 0.0,
    }
    return dst, record


def assert_comparable(records, label="comparison"):
    """Every unit in one comparison must share support, footprint and dimensions. Fails loudly.

    Called before any Pareto computation. A comparison that fails this is not eligible for ranking:
    the ranking would be between different amounts of ground.
    """
    if not records:
        raise ComparabilityError(f"{label}: nothing to compare")
    first_key, first = next(iter(records.items()))
    for key, rec in records.items():
        for field in ("cells", "support_m_requested", "footprint_m"):
            if rec[field] != first[field]:
                raise ComparabilityError(
                    f"{label}: {key} has {field}={rec[field]} but {first_key} has {first[field]}. "
                    f"The units do not cover the same ground, so they cannot be ranked against "
                    f"each other.")
        if not rec.get("exact"):
            raise ComparabilityError(f"{label}: {key} was not built on an exact grid")
    return True


def resolution_gate(record, label="unit"):
    """A unit whose support is below its source's honest floor cannot be compared at that support."""
    if record["support_m_requested"] < record["source_floor_m"]:
        raise ComparabilityError(
            f"{label}: support {record['support_m_requested']} m is below the 3x source floor "
            f"{record['source_floor_m']} m for a {record['source_posting_m']} m product")
    return True
