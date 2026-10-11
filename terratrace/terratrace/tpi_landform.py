"""Topographic Position Index (TPI) slope-position / landform classification,
after Weiss (2001) -- pure-NumPy, map-scale MORPHOLOGY only.

Weiss, A.D. (2001). Topographic position and landforms analysis. ESRI User
Conference poster, San Diego, CA.

The Topographic Position Index of a cell at a given neighbourhood RADIUS is the
cell's elevation minus the MEAN elevation of the cells in a square window of
side ``2*radius+1`` centred on it::

    TPI(radius)[i, j] = z[i, j] - mean( z over the (2r+1)x(2r+1) window at i,j )

A positive TPI marks a cell standing ABOVE its surroundings (a local high --
ridge/hilltop); a negative TPI marks a cell BELOW its surroundings (a local
low -- valley/pit); TPI near zero marks a constant-slope flank or a flat. The
window mean is computed with a summed-area table (cumulative-sum box filter),
NOT a per-cell loop, and is CLIPPED to the grid at the borders so only cells
that exist (and are finite) contribute -- the module is NaN-safe and vectorised.

Weiss (2001) slope-position classification standardises the TPI to zero mean
and unit standard deviation over the grid,

    tpi_std = (TPI - nanmean(TPI)) / nanstd(TPI)

and labels every cell one of SIX slope-position classes from ``tpi_std`` and
the local slope (degrees), using the standard Weiss thresholds:

    ridge         tpi_std >  1
    upper_slope    0.5 < tpi_std <= 1
    middle_slope  -0.5 <= tpi_std <= 0.5  AND  slope >  flat_slope_deg
    flat          -0.5 <= tpi_std <= 0.5  AND  slope <= flat_slope_deg
    lower_slope   -1 <= tpi_std < -0.5
    valley        tpi_std < -1

The single-scale TPI separates highs from lows but not a ridge-top from a flat
(both can have small |tpi_std|); the local slope resolves that ambiguity in the
middle band -- a near-level middle-band cell is ``flat``, a sloping one is a
``middle_slope``. ``flat_slope_deg`` (default 5 deg) is the level/sloping cut.
Slope is ``degrees(arctan(|grad z|))`` from ``np.gradient`` at spacing ``dx``.

Claim firewall: every quantity here is a map-scale MORPHOLOGY descriptor of the
sampled elevation grid. A slope-position class is a descriptive SHAPE label and
nothing more -- it does NOT estimate traversability, trafficability, hazard,
slope stability, mechanical / rock-scale roughness, geologic origin, or rover /
mission behaviour.

Pure NumPy, NaN-safe, deterministic -- no SciPy, no network.
"""
from __future__ import annotations

import warnings

import numpy as np

__all__ = [
    "CLASS_NAMES",
    "tpi",
    "slope_position_classes",
    "tpi_landform_signature",
]

#: Slope-position class names in code order: index ``i`` is class code ``i`` in
#: the int8 map from :func:`slope_position_classes` (-1 = a NaN/undefined cell).
CLASS_NAMES = ("valley", "lower_slope", "flat", "middle_slope",
               "upper_slope", "ridge")

N_CLASSES = len(CLASS_NAMES)


def _validate_radius(radius):
    """Return ``radius`` as a positive int (>= 1), else raise ``ValueError``."""
    r = int(radius)
    if r < 1:
        raise ValueError("radius must be a positive integer (>= 1)")
    return r


def _box_sum(a, window):
    """Clipped moving-window sum via a summed-area table (no per-cell loop).

    For every cell returns the sum of ``a`` over the square window of odd side
    ``window`` centred on it, CLIPPED to the grid at the borders so only cells
    that exist contribute. ``a`` must carry 0 where a cell must not count.
    """
    a = np.asarray(a, dtype=float)
    rows, cols = a.shape
    r = window // 2
    integ = np.zeros((rows + 1, cols + 1), dtype=float)
    integ[1:, 1:] = np.cumsum(np.cumsum(a, axis=0), axis=1)
    i = np.arange(rows)
    j = np.arange(cols)
    i0 = np.clip(i - r, 0, rows)[:, None]
    i1 = np.clip(i + r + 1, 0, rows)[:, None]
    j0 = np.clip(j - r, 0, cols)[None, :]
    j1 = np.clip(j + r + 1, 0, cols)[None, :]
    return integ[i1, j1] - integ[i0, j1] - integ[i1, j0] + integ[i0, j0]


def _box_mean(z, radius):
    """NaN-aware clipped moving-window MEAN over a ``(2*radius+1)``-square window.

    Each cell gets the mean of the FINITE elevations inside its square window,
    clipped at the grid borders; ``nan`` only where a window holds no finite
    cell. Uses two summed-area tables (value sum and finite-count), so it is
    O(N) and loop-free.
    """
    z = np.asarray(z, dtype=float)
    valid = np.isfinite(z)
    window = 2 * radius + 1
    s = _box_sum(np.where(valid, z, 0.0), window)
    n = _box_sum(valid.astype(float), window)
    out = np.full(z.shape, np.nan, dtype=float)
    nz = n > 0.0
    out[nz] = s[nz] / n[nz]
    return out


def _slope_deg(z, dx):
    """Gradient-magnitude slope in degrees from ``np.gradient`` at spacing ``dx``.

    ``slope = degrees(arctan(hypot(dz/dx, dz/dy)))``; for a tilted plane
    ``z = a*x + b*y`` this is ``degrees(arctan(hypot(a, b)))``. NaN propagates
    from any NaN in the difference stencil, so a cell on a NaN margin is ``nan``
    (and falls to the slope-independent branch of the classifier).
    """
    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if not np.isfinite(dx) or dx <= 0.0:
        raise ValueError("dx must be a positive, finite grid spacing")
    gy, gx = np.gradient(z, dx, dx)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def tpi(z, dx=1.0, radius=5):
    """Topographic Position Index at a neighbourhood ``radius`` (Weiss 2001).

    Returns a float64 array shaped like ``z`` whose cell ``[i, j]`` is
    ``z[i, j] - mean(z over the (2*radius+1)-square window centred on [i, j])``,
    the window mean taken over the FINITE cells only and CLIPPED at the grid
    borders (:func:`_box_mean`). Positive = local high (ridge/hilltop), negative
    = local low (valley/pit), ~0 = constant-slope flank or flat. A ``nan`` input
    cell yields ``nan``. ``dx`` is accepted for API symmetry but does not affect
    the (elevation-difference) TPI itself -- the slope-based classifier
    (:func:`slope_position_classes`) is what uses ``dx``. NaN-safe, vectorised.
    """
    r = _validate_radius(radius)
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    return z - _box_mean(z, r)


def _standardize(values):
    """``(values - nanmean) / nanstd`` ignoring NaNs.

    A zero / degenerate spread (e.g. a constant or all-zero TPI field, as from a
    perfectly flat surface) is treated as UNIT spread so the centred values stay
    finite -- a flat surface then standardises to ``0`` everywhere (which the
    classifier reads as the ``flat`` band). An all-NaN field yields all ``nan``.
    """
    values = np.asarray(values, dtype=float)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        mean = np.nanmean(values)
        std = np.nanstd(values)
    if not np.isfinite(mean):
        mean = 0.0
    if not np.isfinite(std) or std == 0.0:
        std = 1.0
    return (values - mean) / std


def slope_position_classes(z, dx=1.0, radius=5, flat_slope_deg=5.0):
    """Weiss (2001) six-class slope-position map (int8; code = CLASS_NAMES index).

    Standardises ``tpi(z, radius)`` to zero mean / unit std over the finite cells
    and labels each cell with the standard Weiss thresholds (see the module
    docstring). Returns an int8 array shaped like ``z`` holding one code per cell:
    ``0=valley, 1=lower_slope, 2=flat, 3=middle_slope, 4=upper_slope, 5=ridge``
    (i.e. the :data:`CLASS_NAMES` index), and ``-1`` where ``z`` is NaN (or the
    TPI is otherwise undefined). The ``flat``/``middle_slope`` split inside the
    middle band uses the ``np.gradient`` slope at spacing ``dx`` against
    ``flat_slope_deg`` (default 5 deg); a cell on a NaN slope margin defaults to
    ``middle_slope``. Vectorised, NaN-safe.
    """
    r = _validate_radius(radius)
    z = np.asarray(z, dtype=float)
    t = tpi(z, dx=dx, radius=r)
    tpi_std = _standardize(t)
    slope = _slope_deg(z, dx)

    valid = np.isfinite(tpi_std)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        is_flat = slope <= float(flat_slope_deg)   # NaN slope -> False -> middle
    mid = valid & (tpi_std >= -0.5) & (tpi_std <= 0.5)

    code = np.full(z.shape, -1, dtype=np.int8)
    code[valid & (tpi_std < -1.0)] = 0                        # valley
    code[valid & (tpi_std >= -1.0) & (tpi_std < -0.5)] = 1    # lower_slope
    code[mid & is_flat] = 2                                   # flat
    code[mid & ~is_flat] = 3                                  # middle_slope
    code[valid & (tpi_std > 0.5) & (tpi_std <= 1.0)] = 4      # upper_slope
    code[valid & (tpi_std > 1.0)] = 5                         # ridge
    return code


def tpi_landform_signature(z, dx=1.0, radius=5):
    """Compact, JSON-serialisable TPI slope-position signature.

    Classifies ``z`` with :func:`slope_position_classes` (default
    ``flat_slope_deg=5`` deg) and returns::

        {"composition": {name: fraction for every name in CLASS_NAMES},
         "dominant_class": name}

    ``composition`` is the area fraction of each of the six classes over the
    VALID (non ``-1``) cells and sums to ~1 (all zeros for an all-NaN /
    degenerate grid). ``dominant_class`` is the class name with the largest
    fraction, ties broken toward the lower :data:`CLASS_NAMES` index
    (``"valley"`` for an empty grid). Carries the module's claim firewall:
    map-scale MORPHOLOGY classification only -- not a traversability, hazard,
    geologic, or mission claim.
    """
    r = _validate_radius(radius)
    classes = slope_position_classes(z, dx=dx, radius=r)
    valid = classes >= 0
    total = int(np.count_nonzero(valid))
    if total:
        counts = np.bincount(classes[valid].astype(np.int64), minlength=N_CLASSES)
    else:
        counts = np.zeros(N_CLASSES, dtype=np.int64)
    composition = {CLASS_NAMES[c]: (float(counts[c]) / total if total else 0.0)
                   for c in range(N_CLASSES)}
    dominant = max(range(N_CLASSES), key=lambda c: composition[CLASS_NAMES[c]])
    return {"composition": composition, "dominant_class": CLASS_NAMES[dominant]}
