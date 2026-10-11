"""Swath / transect profile extractor -- geometric cross-sections of a DEM.

A small, dependency-free analysis utility that samples an elevation grid along a
straight line ``p0 -> p1`` (given in ``(row, col)`` pixel coordinates) with
BILINEAR interpolation, and -- optionally -- over a parallel SWATH of lines, to
produce along-track elevation / slope profiles and a swath envelope. It is a
convenience tool for report figures and quick morphology inspection; the
features the engine actually decides on live in the descriptor modules, not here.

Sampling
--------
``n`` stations are placed at equal fractions ``t in [0, 1]`` along ``p0 -> p1``
(default ``n = ceil(pixel_length) + 1``, i.e. roughly one station per pixel). At
each station the fractional ``(row, col)`` is sampled with standard bilinear
interpolation of the four surrounding cells. A station that falls OUTSIDE the
closed grid ``[0, nrows-1] x [0, ncols-1]`` -- or whose 2x2 interpolation stencil
touches a nodata (NaN) cell -- is returned as NaN rather than raising, so edge
and nodata geometry is handled honestly.

Along-track distance is cumulative metres with uniform step
``(pixel_length / (n - 1)) * dx`` where ``dx`` is the grid spacing in metres;
slope is ``|d(elevation)/d(distance)|`` via :func:`numpy.gradient` (one-sided at
the two ends, central in between). The swath offsets each parallel line
perpendicular to the track by ``k`` pixels (``k*dx`` metres) for
``k in -half_width .. half_width`` and reduces across the swath, NaN-aware, at
every along-track station.

Everything is pure NumPy, deterministic and NaN-safe; all outputs are plain
Python floats / lists so the dicts are directly JSON-serialisable. No SciPy, no
network, no disk.

Scientific boundary / claim firewall: this is a purely GEOMETRIC
cross-section / swath extraction of the sampled height field for visualisation
and analysis -- map-scale morphology only. It is NOT a process, erosion,
hydrology, traversability, trafficability, hazard, geologic-origin, or
mission-readiness claim on Mars, the Moon, Mercury, Ceres, Earth or any other
body; "profile", "slope" and "relief" are used in their abstract grid-geometry
sense.
"""
from __future__ import annotations

import warnings

import numpy as np

__all__ = [
    "extract_profile",
    "swath_profile",
    "transect_signature",
]

def _as_point(p):
    """Return ``(row, col)`` as two plain floats (accepts any 2-sequence)."""
    return float(p[0]), float(p[1])


def _line_stations(p0, p1, n):
    """Sample geometry for a straight line ``p0 -> p1`` in pixel coordinates.

    Returns ``(rows, cols, seg_len_px, n)``: ``rows``/``cols`` are the fractional
    pixel coordinates of ``n`` equally spaced stations (``n`` resolves to
    ``ceil(pixel_length) + 1`` when ``None`` and is clamped to ``>= 1``), and
    ``seg_len_px`` is the Euclidean pixel length of the segment.
    """
    r0, c0 = _as_point(p0)
    r1, c1 = _as_point(p1)
    dr = r1 - r0
    dc = c1 - c0
    seg_len_px = float(np.hypot(dr, dc))
    if n is None:
        n = int(np.ceil(seg_len_px)) + 1
    n = max(1, int(n))
    t = np.zeros(1, dtype=float) if n == 1 else np.linspace(0.0, 1.0, n)
    return r0 + t * dr, c0 + t * dc, seg_len_px, n


def _bilinear_sample(z, rr, cc):
    """Bilinearly interpolate ``z`` at fractional ``(rr, cc)`` pixel coordinates.

    ``rr``/``cc`` are equal-shaped arrays; the return carries that shape. A
    sample outside the closed grid ``[0, nrows-1] x [0, ncols-1]`` -- or whose
    2x2 stencil touches a NaN -- is NaN (never raises). Bilinear weights
    reproduce a linear field exactly, so a planar DEM samples with no error.
    """
    z = np.asarray(z, dtype=float)
    rr = np.asarray(rr, dtype=float)
    cc = np.asarray(cc, dtype=float)
    out = np.full(rr.shape, np.nan, dtype=float)
    if z.ndim != 2 or z.shape[0] < 1 or z.shape[1] < 1:
        return out
    nrows, ncols = z.shape
    valid = (np.isfinite(rr) & np.isfinite(cc)
             & (rr >= 0.0) & (rr <= nrows - 1)
             & (cc >= 0.0) & (cc <= ncols - 1))
    if not np.any(valid):
        return out
    rv = rr[valid]
    cv = cc[valid]
    r0 = np.clip(np.floor(rv).astype(np.intp), 0, nrows - 1)
    c0 = np.clip(np.floor(cv).astype(np.intp), 0, ncols - 1)
    r1 = np.clip(r0 + 1, 0, nrows - 1)
    c1 = np.clip(c0 + 1, 0, ncols - 1)
    fr = rv - r0
    fc = cv - c0
    top = z[r0, c0] * (1.0 - fc) + z[r0, c1] * fc
    bot = z[r1, c0] * (1.0 - fc) + z[r1, c1] * fc
    out[valid] = top * (1.0 - fr) + bot * fr
    return out

def _profile_slope(elevation, step_m):
    """``|d(elevation)/d(distance)|`` along a uniformly spaced profile.

    First-order one-sided differences at the two ends, central differences in
    between (:func:`numpy.gradient`). NaN elevations propagate to their
    neighbours; a profile shorter than two stations, or a non-positive step, has
    undefined slope and is returned all-NaN. Never raises.
    """
    elevation = np.asarray(elevation, dtype=float)
    n = elevation.size
    if n < 2 or not np.isfinite(step_m) or step_m <= 0.0:
        return np.full(n, np.nan, dtype=float)
    with np.errstate(invalid="ignore"):
        return np.abs(np.gradient(elevation, float(step_m)))


def _finite_reduce(fn, a):
    """Apply ``fn`` to the finite entries of ``a`` (NaN if none). No warnings."""
    a = np.asarray(a, dtype=float)
    a = a[np.isfinite(a)]
    return float(fn(a)) if a.size else float("nan")


def extract_profile(z, p0, p1, dx=1.0, n=None):
    """Bilinear elevation / slope profile along the line ``p0 -> p1``.

    ``p0``/``p1`` are ``(row, col)`` pixel coordinates; ``dx`` is the grid
    spacing in metres; ``n`` is the number of along-track stations (default
    ``ceil(pixel_length) + 1``). Returns a JSON-serialisable dict of three
    equal-length lists of plain floats::

        {"distance_m": [...],   # cumulative metres, step = seg_len/(n-1) * dx
         "elevation":  [...],   # bilinearly interpolated height (NaN off-grid)
         "slope":      [...]}   # |d(elevation)/d(distance)|, NaN where undefined

    Off-grid stations and stencils touching nodata are NaN; the call never
    raises. Purely geometric -- see the module claim firewall.
    """
    rows, cols, seg_len_px, n = _line_stations(p0, p1, n)
    elevation = _bilinear_sample(z, rows, cols)
    step_m = (seg_len_px / (n - 1)) * float(dx) if n >= 2 else 0.0
    distance_m = np.arange(n, dtype=float) * step_m
    slope = _profile_slope(elevation, step_m)
    return {
        "distance_m": [float(v) for v in distance_m],
        "elevation": [float(v) for v in elevation],
        "slope": [float(v) for v in slope],
    }

def swath_profile(z, p0, p1, dx=1.0, half_width=5, n=None):
    """Along-track swath envelope over lines parallel to ``p0 -> p1``.

    Samples ``2*half_width + 1`` lines, each the ``p0 -> p1`` track offset
    perpendicular by ``k`` pixels (``k*dx`` metres) for
    ``k in -half_width .. half_width``, and reduces across the swath -- NaN-aware
    -- at every along-track station. Returns a JSON-serialisable dict of five
    equal-length lists of plain floats::

        {"distance_m": [...], "elev_min": [...], "elev_mean": [...],
         "elev_max": [...], "elev_std": [...]}

    By construction ``elev_max >= elev_mean >= elev_min`` at any station with at
    least one finite swath sample. Never raises. Purely geometric.
    """
    base_rows, base_cols, seg_len_px, n = _line_stations(p0, p1, n)
    hw = max(0, int(half_width))
    (r0, c0), (r1, c1) = _as_point(p0), _as_point(p1)
    if seg_len_px > 0.0:
        perp_r, perp_c = -(c1 - c0) / seg_len_px, (r1 - r0) / seg_len_px
    else:
        perp_r = perp_c = 0.0
    lines = [_bilinear_sample(z, base_rows + k * perp_r, base_cols + k * perp_c)
             for k in range(-hw, hw + 1)]
    stack = np.vstack(lines)
    step_m = (seg_len_px / (n - 1)) * float(dx) if n >= 2 else 0.0
    distance_m = np.arange(n, dtype=float) * step_m
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        emin = np.nanmin(stack, axis=0)
        emean = np.nanmean(stack, axis=0)
        emax = np.nanmax(stack, axis=0)
        estd = np.nanstd(stack, axis=0)
    return {
        "distance_m": [float(v) for v in distance_m],
        "elev_min": [float(v) for v in emin],
        "elev_mean": [float(v) for v in emean],
        "elev_max": [float(v) for v in emax],
        "elev_std": [float(v) for v in estd],
    }

def transect_signature(z, p0, p1, dx=1.0):
    """Compact scalar summary of the ``p0 -> p1`` transect.

    Returns a flat, JSON-serialisable dict of plain floats::

        {"length_m":    float,   # along-track length  = pixel_length * dx
         "relief_m":    float,   # max(elev) - min(elev) over finite stations
         "max_slope":   float,   # max |d(elev)/d(dist)| over finite stations
         "mean_slope":  float,   # mean |d(elev)/d(dist)| over finite stations
         "elev_gain_m": float}   # elevation[-1] - elevation[0] (signed)

    NaN-safe (reductions ignore non-finite stations; a NaN endpoint yields a NaN
    ``elev_gain_m``) and deterministic. Purely geometric -- see the firewall.
    """
    prof = extract_profile(z, p0, p1, dx=dx, n=None)
    elev = np.asarray(prof["elevation"], dtype=float)
    slope = np.asarray(prof["slope"], dtype=float)
    dist = np.asarray(prof["distance_m"], dtype=float)
    length_m = float(dist[-1] - dist[0]) if dist.size else float("nan")
    finite_elev = elev[np.isfinite(elev)]
    if finite_elev.size:
        relief_m = float(finite_elev.max() - finite_elev.min())
    else:
        relief_m = float("nan")
    if elev.size and np.isfinite(elev[0]) and np.isfinite(elev[-1]):
        elev_gain = float(elev[-1] - elev[0])
    else:
        elev_gain = float("nan")
    return {
        "length_m": length_m,
        "relief_m": relief_m,
        "max_slope": _finite_reduce(np.max, slope),
        "mean_slope": _finite_reduce(np.mean, slope),
        "elev_gain_m": elev_gain,
    }




