"""Differential box-counting (DBC) fractal dimension of an elevation surface.

Treats an elevation grid as a gray-scale image and estimates the fractal
(box-counting) dimension of its surface with the differential box-counting
method, a compact single-number index of map-scale surface complexity /
roughness: a planar surface measures ~2.0, a maximally rough (space-filling)
surface approaches 3.0.

Sarkar, N. & Chaudhuri, B.B. (1994). An efficient differential box-counting
approach to compute fractal dimension of images. IEEE Trans. SMC 24(1),
115-120.

Method
------
Non-finite cells are first filled with the finite mean (0.0 if nothing is
finite) -- the module's documented nodata policy. The heights are then scaled
into the SAME units as the pixel grid so the measure is isotropic::

    g = (z - zmin) / (zmax - zmin) * (M - 1),     M = min(nrows, ncols)

so one gray level equals one pixel step and a box of side ``s`` is a true
``s x s x s`` cube in (row, col, height) space. A relief-free grid
(``zmax == zmin``) has no surface structure and is reported as dimension
exactly 2.0.

For each box size ``s`` in a geometric set (``s = 2, 3, 4, 6, 8, ...`` up to
``M // 2``) the grid is tiled into non-overlapping ``s x s`` blocks. Within a
block the surface spans gray levels ``gmin .. gmax``; the number of vertical
boxes of height ``s`` needed to cover that column is

    n = floor(gmax / s) - floor(gmin / s) + 1        (always >= 1)

and ``N(s) = sum of n over all blocks``. On a self-affine surface
``N(s) ~ (1 / s) ** D``, so the dimension is the least-squares slope of
``log(N(s))`` against ``log(1 / s)``. It is clamped to the physically
meaningful range ``[2, 3]`` and reported with the fit's coefficient of
determination ``r2`` as a quality flag.

Everything is pure NumPy and vectorised per box size (a strided reshape gives
the per-block min/max with no per-cell Python loop; only the handful of box
sizes are looped), NaN-safe, deterministic, and fast (<1 s on 256x256). No
SciPy, no network, no disk.

Scientific boundary / claim firewall
-------------------------------------
The box-counting dimension is a MAP-SCALE MORPHOLOGY descriptor of the sampled
elevation grid ONLY -- a scalar summary of surface roughness / geometric
complexity. It is NOT a traversability, trafficability, hazard, slope-stability,
geologic-origin, resource, or mission-readiness claim, and says nothing about
rock-scale obstacles below the pixel scale.
"""
from __future__ import annotations

import numpy as np

__all__ = ["box_counting_dimension", "fractal_signature"]


def _fill_nan_mean(z):
    """Return a float copy of ``z`` with non-finite cells set to the finite
    mean (0.0 if nothing is finite). The documented NaN policy of the module."""
    z = np.array(z, dtype=float, copy=True)
    bad = ~np.isfinite(z)
    if bad.any():
        good = z[~bad]
        z[bad] = float(good.mean()) if good.size else 0.0
    return z


def _scaled_gray(z):
    """Fill NaNs, then scale heights into pixel-grid units ``[0, M - 1]``.

    Returns ``(g, M, degenerate)`` where ``g`` is the scaled gray surface
    (``None`` when degenerate), ``M = min(nrows, ncols)``, and ``degenerate``
    is True for a relief-free grid (``zmax == zmin``), which has no surface
    structure and is reported as dimension exactly 2.0.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("box-counting dimension needs a 2-D elevation grid")
    z = _fill_nan_mean(z)
    nr, nc = z.shape
    M = min(nr, nc)
    zmin = float(z.min())
    zmax = float(z.max())
    rng = zmax - zmin
    if not np.isfinite(rng) or rng <= 0.0:
        return None, M, True
    g = (z - zmin) / rng * (M - 1)
    return g, M, False


def _box_sizes(M):
    """Geometric ladder of box sizes ``2, 3, 4, 6, 8, ...`` up to ``M // 2``.

    Grows by a factor of sqrt(2) and rounds to the nearest integer, dropping
    duplicates so the sequence is strictly increasing (dyadic steps 2, 4, 8,
    16, ... land exactly). Fewer than three usable sizes means the grid is too
    small for a slope estimate.
    """
    half = M // 2
    sizes = []
    s = 2.0
    while True:
        si = int(round(s))
        if si > half:
            break
        if si >= 2 and (not sizes or si > sizes[-1]):
            sizes.append(si)
        s *= 2.0 ** 0.5
    return sizes


def _box_counts(g, sizes):
    """Vectorised differential box count ``N(s)`` for each ``s`` in ``sizes``.

    For every box size the grid is cropped to whole blocks, reshaped into
    non-overlapping ``s x s`` tiles via a strided ``(nbr, s, nbc, s)`` view, and
    the per-block gray min/max are taken over the block axes (no per-cell Python
    loop). ``n = floor(gmax/s) - floor(gmin/s) + 1`` per block (>= 1), summed.
    """
    nr, nc = g.shape
    counts = []
    for s in sizes:
        nbr = nr // s
        nbc = nc // s
        cropped = g[:nbr * s, :nbc * s]
        blocks = cropped.reshape(nbr, s, nbc, s)
        bmin = blocks.min(axis=(1, 3))
        bmax = blocks.max(axis=(1, 3))
        n = np.floor(bmax / s) - np.floor(bmin / s) + 1.0
        counts.append(float(n.sum()))
    return counts


def _loglog_fit(sizes, counts):
    """Least-squares fit of ``log(N(s))`` vs ``log(1 / s)``.

    Returns ``(D, r2)`` with the slope ``D`` clamped to ``[2, 3]`` and the
    coefficient of determination ``r2`` clamped to ``[0, 1]`` (1.0 when the
    counts carry no variance to explain).
    """
    s = np.asarray(sizes, dtype=float)
    N = np.asarray(counts, dtype=float)
    x = np.log(1.0 / s)
    y = np.log(N)
    slope, intercept = np.polyfit(x, y, 1)
    yhat = slope * x + intercept
    ss_res = float(np.sum((y - yhat) ** 2))
    ss_tot = float(np.sum((y - y.mean()) ** 2))
    r2 = 1.0 - ss_res / ss_tot if ss_tot > 0.0 else 1.0
    r2 = min(1.0, max(0.0, r2))
    D = min(3.0, max(2.0, float(slope)))
    return D, r2


def box_counting_dimension(z):
    """Differential box-counting fractal dimension of elevation grid ``z``.

    Returns a plain ``float`` in ``[2, 3]`` (Sarkar & Chaudhuri 1994): ~2.0 for a
    planar surface, approaching 3.0 for a maximally rough / space-filling one. A
    relief-free grid (``zmax == zmin``) returns exactly ``2.0``. Returns ``nan``
    only when the grid is too small to yield at least three usable box sizes.
    NaN-safe (non-finite cells filled with the finite mean) and deterministic.
    """
    g, M, degenerate = _scaled_gray(z)
    if degenerate:
        return 2.0
    sizes = _box_sizes(M)
    if len(sizes) < 3:
        return float("nan")
    counts = _box_counts(g, sizes)
    D, _r2 = _loglog_fit(sizes, counts)
    return D


def fractal_signature(z):
    """Compact, JSON-serialisable box-counting signature of ``z``.

    Returns plain Python scalars::

        {"box_count_dimension": float,   # D in [2, 3]; NaN if < 3 box sizes
         "r2": float,                     # fit quality in [0, 1]
         "n_scales": int}                 # number of box sizes used

    A relief-free grid gives ``{2.0, 1.0, n_scales}`` (planar surface, perfect
    fit); a grid too small for three box sizes gives ``{nan, nan, n_scales}``.
    Carries the module's claim firewall: map-scale surface-roughness morphology
    only -- not a traversability, hazard, geologic, or mission claim.
    """
    g, M, degenerate = _scaled_gray(z)
    sizes = _box_sizes(M)
    n_scales = len(sizes)
    if degenerate:
        return {"box_count_dimension": 2.0, "r2": 1.0, "n_scales": n_scales}
    if n_scales < 3:
        nan = float("nan")
        return {"box_count_dimension": nan, "r2": nan, "n_scales": n_scales}
    counts = _box_counts(g, sizes)
    D, r2 = _loglog_fit(sizes, counts)
    return {"box_count_dimension": float(D), "r2": float(r2),
            "n_scales": int(n_scales)}
