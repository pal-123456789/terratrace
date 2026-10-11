"""Iwahashi & Pike (2007) three-part geometric signature + nested-means terrain
classification -- a recognised, citable automated terrain-classification method,
implemented in pure NumPy as a map-scale MORPHOLOGY descriptor (complementary to
the geomorphon landform classifier).

Iwahashi, J., & Pike, R. J. (2007). Automated classifications of topography from
DEMs by an unsupervised nested-means algorithm and a three-part geometric
signature. Geomorphology, 86(3-4), 409-440.

The method describes every cell by a THREE-PART geometric signature, each part a
per-cell quantity reduced to a moving-window frequency:

1. Slope (degrees) -- the standard gradient-magnitude slope of the DEM at
   spacing ``dx`` (reused here from :func:`terratrace.features.slope_deg`).

2. Local convexity -- a cell is "convex" (a local topographic HIGH) iff its
   centre sits strictly above the mean of its four cardinal neighbours::

       4*z[i, j] - (z[i-1, j] + z[i+1, j] + z[i, j-1] + z[i, j+1]) > 0

   i.e. a strictly NEGATIVE discrete Laplacian (the five-point stencil
   ``neighbour_sum - 4*centre`` approximates ``dx**2 * laplacian(z)``, so the
   quantity above is ``-dx**2 * laplacian(z)`` and is > 0 exactly where the
   surface bulges upward). :func:`local_convexity` returns, per cell, the
   PERCENTAGE (0..100) of convex cells inside a square moving window of odd side
   ``window``. Sign convention is explicit: convex == local high == centre above
   its four-neighbour mean == negative discrete Laplacian.

3. Surface texture ("pit-and-peak" frequency) -- the DEM is 3x3 median filtered,
   the residual ``d = z - median3x3`` is formed, and a cell is a pit/peak iff
   ``abs(d) > texture_threshold`` (default 1.0 m). :func:`surface_texture`
   returns, per cell, the PERCENTAGE (0..100) of pit/peak cells inside the
   square moving window. ``texture_threshold`` is a resolution-dependent
   PARAMETER in the DEM's elevation units (metres).

The two moving-window frequencies are computed with a summed-area table
(cumulative-sum box filter), NOT a per-cell Python loop; windows are CLIPPED to
the grid at the borders and each frequency is taken over the VALID (defined,
finite) cells only, so the whole module is NaN-safe.

First-level nested-means classification (8 classes), after Iwahashi & Pike
(2007): with ``t_slope = nanmean(slope)`` the grid is split into STEEP
(``slope >= t_slope``) and GENTLE (``slope < t_slope``); WITHIN each slope group
its OWN ("nested") means of the convexity and texture maps give the per-group
thresholds ``t_conv_group`` / ``t_text_group``, and each cell's class code is

    4*(slope >= t_slope) + 2*(convexity >= t_conv_group) + 1*(texture >= t_text_group)

giving 8 classes (0..7). This is the FIRST-LEVEL nested-means classification
only; the window size and the texture threshold are resolution-dependent
parameters, and it is NOT claimed to reproduce IP07's exact iterative 12-/16-
class product (which recurses the nested-means split on the gentle subset). It
is documented honestly as a first-level, 8-class geometric-signature classifier
in the spirit of the published method.

Claim firewall: every quantity here is a map-scale MORPHOLOGY descriptor of the
sampled elevation grid. None of it estimates traversability, trafficability,
mechanical / rock-scale roughness, geologic origin, or rover / mission
behaviour; a terrain class is a descriptive SHAPE label, nothing more.

Pure NumPy, NaN-safe, deterministic -- no SciPy, no network.
"""
from __future__ import annotations

import warnings

import numpy as np

from . import features

__all__ = [
    "local_convexity",
    "surface_texture",
    "geometric_signature",
    "nested_means_classes",
    "terrain_class_composition",
    "iwahashi_pike_signature",
]

#: Number of first-level nested-means classes (codes 0..7).
N_CLASSES = 8

#: Relative floating-point-noise tolerance. Used both for the convexity sign
#: test and for the nested-means threshold comparisons so that a (near-)constant
#: signature field -- e.g. a perfectly planar DEM, whose discrete Laplacian is
#: zero and whose slope is uniform in exact arithmetic -- collapses to a single
#: class rather than being split by rounding noise. It is ~1e6x above the
#: observed noise floor and far below any real terrain variation, so it never
#: affects a genuine classification.
_RTOL = 1e-9


def _validate_window(window):
    """Return ``window`` as a positive ODD int, else raise ``ValueError``."""
    w = int(window)
    if w < 1:
        raise ValueError("window must be a positive odd integer")
    if w % 2 == 0:
        raise ValueError("window must be an odd integer")
    return w


def _nanmean(a):
    """nan-robust mean of an array's finite entries (``nan`` if none)."""
    a = np.asarray(a, dtype=float)
    finite = a[np.isfinite(a)]
    if finite.size == 0:
        return float("nan")
    return float(np.mean(finite))


def _box_sum(a, window):
    """Clipped moving-window sum via a summed-area table (no per-cell loop).

    For every cell returns the sum of ``a`` over the square window of odd side
    ``window`` centred on it, CLIPPED to the grid at the borders so only cells
    that exist contribute. ``a`` should carry 0 where a cell must not count.
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


def _window_percent(flag, valid, window):
    """Percentage (0..100) of flagged cells among the VALID cells of each
    clipped window; ``nan`` where a window has no valid cell."""
    num = _box_sum(np.where(flag, 1.0, 0.0), window)
    den = _box_sum(np.where(valid, 1.0, 0.0), window)
    out = np.full(num.shape, np.nan, dtype=float)
    nz = den > 0.0
    out[nz] = 100.0 * num[nz] / den[nz]
    return out


def _convexity_flags(z):
    """Per-cell discrete convexity test -> ``(convex, valid)`` boolean maps.

    ``convex`` is True where ``4*z - (up + down + left + right) > 0`` (centre
    strictly above its four-neighbour mean; a negative discrete Laplacian).
    ``valid`` marks cells with a complete, finite four-neighbour stencil (the
    outermost ring and any NaN-adjacent cell have an undefined convexity).
    """
    z = np.asarray(z, dtype=float)
    zp = np.pad(z, 1, mode="constant", constant_values=np.nan)
    centre = zp[1:-1, 1:-1]
    up = zp[:-2, 1:-1]
    down = zp[2:, 1:-1]
    left = zp[1:-1, :-2]
    right = zp[1:-1, 2:]
    lap = 4.0 * centre - (up + down + left + right)
    valid = np.isfinite(lap)
    finite_z = z[np.isfinite(z)]
    zscale = float(np.max(np.abs(finite_z))) if finite_z.size else 0.0
    tol = _RTOL * max(1.0, zscale)
    convex = valid & (lap > tol)
    return convex, valid


def _median3x3(z):
    """Pure-NumPy, NaN-aware 3x3 median by stacking the nine shifted planes."""
    z = np.asarray(z, dtype=float)
    rows, cols = z.shape
    zp = np.pad(z, 1, mode="constant", constant_values=np.nan)
    planes = [zp[di:di + rows, dj:dj + cols]
              for di in range(3) for dj in range(3)]
    stack = np.stack(planes, axis=0)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmedian(stack, axis=0)


def local_convexity(z, dx=1.0, window=11):
    """Moving-window percentage (0..100) of locally CONVEX cells.

    A cell is convex iff ``4*z - (up + down + left + right) > 0`` -- its centre
    sits strictly above the mean of its four cardinal neighbours (a negative
    discrete Laplacian; a local topographic high). The strict ``> 0`` test is
    evaluated just above the floating-point-noise floor (see :data:`_RTOL`), so
    a planar surface -- whose Laplacian is identically zero in exact arithmetic
    -- is not spuriously flagged convex by rounding error. The returned float64
    array
    (shape of ``z``) holds, per cell, the percentage of convex cells inside the
    square moving window of odd side ``window``, taken over the window's VALID
    (defined, finite) cells and CLIPPED at the grid borders; ``nan`` where a
    window has no valid cell. ``dx`` is accepted for API symmetry but does not
    affect the (scale-invariant) convexity sign test. NaN-safe, vectorised.
    """
    window = _validate_window(window)
    convex, valid = _convexity_flags(z)
    return _window_percent(convex, valid, window)


def surface_texture(z, dx=1.0, window=11, texture_threshold=1.0):
    """Moving-window percentage (0..100) of pit/peak ("textured") cells.

    The DEM is 3x3 median filtered; the residual ``d = z - median3x3`` is
    formed; a cell is a pit/peak iff ``abs(d) > texture_threshold``. The
    returned float64 array (shape of ``z``) holds, per cell, the percentage of
    pit/peak cells inside the square moving window of odd side ``window``, taken
    over the window's VALID (finite-residual) cells and CLIPPED at the grid
    borders; ``nan`` where a window has no valid cell. ``texture_threshold`` is
    a resolution-dependent PARAMETER in the DEM's elevation units (metres);
    ``dx`` is accepted for API symmetry but is not used. NaN-safe, vectorised.
    """
    window = _validate_window(window)
    z = np.asarray(z, dtype=float)
    med = _median3x3(z)
    d = z - med
    valid = np.isfinite(d)
    pit_peak = valid & (np.abs(d) > float(texture_threshold))
    return _window_percent(pit_peak, valid, window)


def geometric_signature(z, dx=1.0, window=11, texture_threshold=1.0):
    """The three-part geometric signature reduced to nan-robust tile means.

    Returns ``{"slope_mean", "convexity_mean", "texture_mean"}`` as plain floats:
    the whole-tile nan-robust means of the slope (degrees), the
    :func:`local_convexity` percentage map and the :func:`surface_texture`
    percentage map. A mean is ``nan`` only if its map has no finite cell.
    """
    window = _validate_window(window)
    z = np.asarray(z, dtype=float)
    slope = features.slope_deg(z, dx, dx)
    conv = local_convexity(z, dx=dx, window=window)
    text = surface_texture(z, dx=dx, window=window,
                           texture_threshold=texture_threshold)
    return {
        "slope_mean": _nanmean(slope),
        "convexity_mean": _nanmean(conv),
        "texture_mean": _nanmean(text),
    }


def _group_mean(arr, mask):
    """Mean of ``arr`` over the finite cells selected by ``mask`` (nan if none)."""
    vals = np.asarray(arr, dtype=float)[mask]
    vals = vals[np.isfinite(vals)]
    if vals.size == 0:
        return float("nan")
    return float(np.mean(vals))


def _ge(values, threshold):
    """``values >= threshold`` with a small scale-aware floating-point tolerance.

    Returns a boolean map ``values >= threshold - tol`` where ``tol`` is
    :data:`_RTOL` times the field's own magnitude scale. This keeps the ``>=``
    nested-means convention of Iwahashi & Pike (2007) while preventing a
    (near-)constant field from being split by rounding noise around its mean.
    ``threshold`` may be a scalar or an array; ``nan`` values compare False.
    """
    v = np.asarray(values, dtype=float)
    finite = v[np.isfinite(v)]
    scale = float(np.max(np.abs(finite))) if finite.size else 1.0
    tol = _RTOL * max(1.0, scale)
    return v >= (threshold - tol)


def nested_means_classes(z, dx=1.0, window=11, texture_threshold=1.0):
    """First-level nested-means terrain classes (int8 map, codes 0..7; -1 = NaN).

    After Iwahashi & Pike (2007): ``t_slope = nanmean(slope)`` splits the grid
    into STEEP (``slope >= t_slope``) and GENTLE (``slope < t_slope``); within
    each slope group its OWN ("nested") means of the convexity and texture maps
    give the per-group thresholds, and the class code is
    ``4*(slope >= t_slope) + 2*(convexity >= t_conv_group) + 1*(texture >=
    t_text_group)`` (8 classes). Cells where ``z`` is NaN -- or where a signature
    is undefined at a NaN margin -- are labelled ``-1``. First-level 8-class
    scheme only (see the module docstring); window / threshold are
    resolution-dependent parameters.
    """
    window = _validate_window(window)
    z = np.asarray(z, dtype=float)
    slope = features.slope_deg(z, dx, dx)
    conv = local_convexity(z, dx=dx, window=window)
    text = surface_texture(z, dx=dx, window=window,
                           texture_threshold=texture_threshold)

    valid = (np.isfinite(z) & np.isfinite(slope)
             & np.isfinite(conv) & np.isfinite(text))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        t_slope = np.nanmean(np.where(valid, slope, np.nan))
    steep_hi = _ge(slope, t_slope)
    steep = valid & steep_hi
    gentle = valid & ~steep_hi

    # Nested (group-specific) convexity / texture thresholds.
    t_conv = np.where(steep, _group_mean(conv, steep), _group_mean(conv, gentle))
    t_text = np.where(steep, _group_mean(text, steep), _group_mean(text, gentle))

    code = (4 * steep.astype(np.int16)
            + 2 * (valid & _ge(conv, t_conv)).astype(np.int16)
            + (valid & _ge(text, t_text)).astype(np.int16)).astype(np.int8)
    code[~valid] = -1
    return code

def terrain_class_composition(z, dx=1.0, window=11, texture_threshold=1.0):
    """Area fraction of each first-level class over the classified cells.

    Returns ``{str(code): fraction}`` for every code ``"0".."7"`` (absent
    classes map to 0.0), summing to ~1.0 over the valid (non ``-1``) cells of
    :func:`nested_means_classes`. An all-NaN / fully-degenerate grid yields all
    zeros. JSON-serialisable (string keys, plain-float values).
    """
    classes = nested_means_classes(z, dx=dx, window=window,
                                   texture_threshold=texture_threshold)
    valid = classes >= 0
    total = int(np.count_nonzero(valid))
    if total:
        counts = np.bincount(classes[valid].astype(np.int64),
                             minlength=N_CLASSES)
    else:
        counts = np.zeros(N_CLASSES, dtype=np.int64)
    return {str(c): (float(counts[c]) / total if total else 0.0)
            for c in range(N_CLASSES)}


def iwahashi_pike_signature(z, dx=1.0):
    """Compact, JSON-serialisable Iwahashi & Pike (2007) terrain signature.

    Combines the three-part :func:`geometric_signature` tile means with the
    first-level nested-means :func:`terrain_class_composition` (both at the
    default ``window=11`` and ``texture_threshold=1.0`` m) into::

        {"slope_mean": float, "convexity_mean": float, "texture_mean": float,
         "composition": {"0": frac, ..., "7": frac},
         "dominant_class": int}        # the most common class code (0..7)

    ``dominant_class`` is the class with the largest area fraction, ties broken
    by the lowest code; it is ``0`` for an empty / degenerate grid. Carries the
    module's claim firewall: map-scale MORPHOLOGY classification only -- not a
    traversability, hazard, geologic, or mission claim.
    """
    sig = geometric_signature(z, dx=dx)
    comp = terrain_class_composition(z, dx=dx)
    dominant = int(max(range(N_CLASSES), key=lambda c: comp[str(c)]))
    return {
        "slope_mean": sig["slope_mean"],
        "convexity_mean": sig["convexity_mean"],
        "texture_mean": sig["texture_mean"],
        "composition": comp,
        "dominant_class": dominant,
    }

