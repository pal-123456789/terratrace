"""Translational DEM co-registration (shift-only horizontal + vertical datum).

Before two same-grid elevation arrays can be differenced or compared
pixel-by-pixel they must be aligned. This module estimates and applies a
TRANSLATION-ONLY, map-scale alignment: an integer (then sub-pixel-refined)
horizontal pixel shift plus a single vertical-datum (bias) offset. It performs
NO rotation, NO scaling, and NO non-rigid warping, and makes NO mechanical or
mission claim about how either DEM was produced or acquired -- it is purely a
numerical alignment of two grids so their overlap can be studied.

All routines are pure NumPy and NaN-aware: cells that are nodata in either
array are ignored, and shifted-in edges are filled with NaN (never wrapped).

Sign convention (self-consistent across this module):
  apply_shift(field, dy, dx) moves content by +dy rows DOWN and +dx cols RIGHT,
  filling vacated edges with NaN. estimate_shift(ref, moving) returns the
  (dy, dx) that, when applied to `moving`, re-aligns it onto `ref`; so for
  moving = apply_shift(ref, dy0, dx0) it recovers (dy, dx) = (-dy0, -dx0).
"""
from __future__ import annotations

import numpy as np


def apply_shift(field, dy, dx):
    """Shift `field` by integer (dy, dx) pixels, NaN-filling vacated edges.

    Positive dy shifts down (towards higher row index); positive dx shifts
    right. Non-integer dy/dx are rounded to the nearest int. Edges exposed by
    the shift are set to NaN (no wrap-around). Returns a new float64 array.
    """
    arr = np.asarray(field, dtype="float64")
    dy = int(round(float(dy)))
    dx = int(round(float(dx)))
    rows, cols = arr.shape
    out = np.full_like(arr, np.nan)
    # dest[i, j] = src[i - dy, j - dx]
    sr0, sr1 = max(0, -dy), min(rows, rows - dy)
    sc0, sc1 = max(0, -dx), min(cols, cols - dx)
    dr0, dr1 = max(0, dy), min(rows, rows + dy)
    dc0, dc1 = max(0, dx), min(cols, cols + dx)
    if sr1 > sr0 and sc1 > sc0:
        out[dr0:dr1, dc0:dc1] = arr[sr0:sr1, sc0:sc1]
    return out


def overlap_rmse(a, b):
    """RMSE over cells that are finite in BOTH arrays (nan if no overlap)."""
    a = np.asarray(a, dtype="float64")
    b = np.asarray(b, dtype="float64")
    mask = np.isfinite(a) & np.isfinite(b)
    if not np.any(mask):
        return float("nan")
    d = a[mask] - b[mask]
    return float(np.sqrt(np.mean(d * d)))


def estimate_vertical_offset(ref, moving):
    """Datum/bias estimate: median(moving - ref) over co-located finite cells.

    Returns nan if the two arrays share no finite cell.
    """
    ref = np.asarray(ref, dtype="float64")
    moving = np.asarray(moving, dtype="float64")
    mask = np.isfinite(ref) & np.isfinite(moving)
    if not np.any(mask):
        return float("nan")
    return float(np.median(moving[mask] - ref[mask]))


def _vertex_offset(y_lo, y_mid, y_hi):
    """Offset of a parabola's vertex through (-1, y_lo), (0, y_mid), (1, y_hi).

    Returns 0.0 when the samples are not convex (no interior minimum) or the
    fit is degenerate. Clamped to [-1, 1] for safety.
    """
    denom = y_lo - 2.0 * y_mid + y_hi
    if not np.isfinite(denom) or denom <= 0.0:
        return 0.0
    off = 0.5 * (y_lo - y_hi) / denom
    if not np.isfinite(off):
        return 0.0
    return float(np.clip(off, -1.0, 1.0))


def estimate_shift(ref, moving, max_shift=5):
    """Find the integer shift that best re-aligns `moving` onto `ref`.

    Searches integer (dy, dx) each in [-max_shift, max_shift]. Each candidate
    shift is applied to `moving` and scored by the overlap RMSE to `ref` AFTER
    removing that candidate's own median vertical offset -- so a pure vertical
    datum bias cannot bias the horizontal search. The minimum-RMSE integer
    shift is then refined to sub-pixel by fitting a parabola to the RMSE at the
    best dx-1/dx/dx+1 (and dy-1/dy/dy+1) and taking the vertex.

    Returns {"dy", "dx", "dy_subpix", "dx_subpix", "rmse", "max_shift"}.
    """
    ref = np.asarray(ref, dtype="float64")
    moving = np.asarray(moving, dtype="float64")
    m = int(max_shift)

    scores = {}
    best = None  # (dy, dx, rmse)
    for dy in range(-m, m + 1):
        for dx in range(-m, m + 1):
            shifted = apply_shift(moving, dy, dx)
            off = estimate_vertical_offset(ref, shifted)
            r = float("nan") if np.isnan(off) else overlap_rmse(ref, shifted - off)
            scores[(dy, dx)] = r
            if not np.isnan(r) and (best is None or r < best[2]):
                best = (dy, dx, r)

    if best is None:
        return {"dy": 0, "dx": 0, "dy_subpix": 0.0, "dx_subpix": 0.0,
                "rmse": float("nan"), "max_shift": m}

    dy_b, dx_b, r_b = best

    yl, yr = scores.get((dy_b - 1, dx_b), np.nan), scores.get((dy_b + 1, dx_b), np.nan)
    dy_sub = dy_b + _vertex_offset(yl, r_b, yr) if (np.isfinite(yl) and np.isfinite(yr)) else float(dy_b)

    xl, xr = scores.get((dy_b, dx_b - 1), np.nan), scores.get((dy_b, dx_b + 1), np.nan)
    dx_sub = dx_b + _vertex_offset(xl, r_b, xr) if (np.isfinite(xl) and np.isfinite(xr)) else float(dx_b)

    return {"dy": int(dy_b), "dx": int(dx_b),
            "dy_subpix": float(dy_sub), "dx_subpix": float(dx_sub),
            "rmse": float(r_b), "max_shift": m}


def coregister(ref, moving, max_shift=5):
    """Estimate and apply a translation + vertical-datum alignment of `moving`.

    Runs estimate_shift, applies the integer (dy, dx) to `moving`, then removes
    the residual median vertical offset so the result best matches `ref`.

    Returns {"dy", "dx", "dy_subpix", "dx_subpix", "rmse", "vertical_offset",
    "aligned"}, where "aligned" is the shifted `moving` with the vertical offset
    subtracted.
    """
    ref = np.asarray(ref, dtype="float64")
    moving = np.asarray(moving, dtype="float64")
    est = estimate_shift(ref, moving, max_shift=max_shift)
    shifted = apply_shift(moving, est["dy"], est["dx"])
    voff = estimate_vertical_offset(ref, shifted)
    if np.isnan(voff):
        aligned = shifted
    else:
        aligned = shifted - voff
    return {"dy": est["dy"], "dx": est["dx"],
            "dy_subpix": est["dy_subpix"], "dx_subpix": est["dx_subpix"],
            "rmse": est["rmse"], "vertical_offset": float(voff),
            "aligned": aligned}
