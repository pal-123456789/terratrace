"""Two-scale (multi-scale) Weiss (2001) TPI slope-position classification --
pure-NumPy, map-scale MORPHOLOGY only.

Weiss, A.D. (2001). Topographic position and landforms analysis. ESRI User
Conference poster, San Diego, CA.  (The SAME citation already carried by the
single-scale :mod:`terratrace.tpi_landform`; this is a DISTINCT, two-scale
descriptor that shares only that reference.)

Where :mod:`terratrace.tpi_landform` reads position from ONE neighbourhood
radius, this module NESTS two radii -- a SMALL and a LARGE window -- as Weiss
(2001) proposes for resolving slope position at two scales at once. The
standardised Topographic Position Index at a neighbourhood radius ``R`` is

    TPI_R[i, j] = z[i, j] - mean( z over the (2R+1)-square window at [i, j] )
    sTPI_R      = (TPI_R - mean(TPI_R)) / std(TPI_R)   # z-scores over finite TPI

each window mean taken with a summed-area table (integral image) so it is O(1).
The mean is NaN-aware and CLIPPED at the borders: only finite cells inside the
(clipped) window contribute, and a window with no finite cell yields a NaN TPI
(that cell is left unclassified). Standardisation uses the finite TPI only.

Each cell is then labelled from the PAIR (small-scale z-score ``sS``, large-scale
z-score ``sL``), thresholded at +/-1 standard deviation::

    sS >  1   and sL >  1   -> "hilltop"
    sS >  1   and |sL| <= 1 -> "upper_slope_ridge"
    sS < -1   and sL < -1   -> "valley"
    sS < -1   and |sL| <= 1 -> "lower_slope_channel"
    |sS| <= 1 and sL >  1   -> "upper_slope"
    |sS| <= 1 and sL < -1   -> "lower_slope"
    otherwise               -> "flat_midslope"   (both ~0, or a mixed-sign corner)

The two mixed-sign corners (a local high on a regional low, or a local low on a
regional high) fall into ``flat_midslope`` by the ``otherwise`` rule. This is an
HONEST 7-label REDUCTION of Weiss's (2001) two-scale scheme (whose full
standardised-TPI cross-tabulation enumerates ten classes) -- NOT a claim to
reproduce that verbatim ten-class table, only the small-vs-large / +/-1-sigma
logic above collapsed to seven named classes.

Scientific boundary / claim firewall: every quantity here is purely GEOMETRIC, a
map-scale topographic-POSITION descriptor of the sampled elevation grid -- a
nested (two-scale) SHAPE label and nothing more. A class name such as "valley",
"hilltop" or "channel" is a descriptive morphometric position only; it does NOT
assert a geological unit or origin, a surface/hydrological PROCESS (water,
erosion, deposition), traversability, trafficability, slope stability, hazard, or
any rover / mission behaviour, on Mars, the Moon, Mercury, Ceres, Earth or any
other body.

Pure NumPy, NaN-safe, deterministic -- no SciPy, no network, no disk.
"""
from __future__ import annotations

import warnings

import numpy as np

__all__ = [
    "CLASS_NAMES",
    "CODE_TO_NAME",
    "SENTINEL",
    "multiscale_tpi_classes",
    "multiscale_tpi_signature",
]

#: Sentinel class code for a NaN / undefined (unclassifiable) cell.
SENTINEL = -1

#: Two-scale slope-position class names in code order (list index == class code),
#: ordered LOW position -> HIGH; :data:`SENTINEL` (-1) marks a NaN/undefined cell.
CLASS_NAMES = (
    "valley",               # 0  sS < -1 and sL < -1
    "lower_slope_channel",  # 1  sS < -1 and |sL| <= 1
    "lower_slope",          # 2  |sS| <= 1 and sL < -1
    "flat_midslope",        # 3  both near zero, or a mixed-sign corner
    "upper_slope",          # 4  |sS| <= 1 and sL >  1
    "upper_slope_ridge",    # 5  sS > 1 and |sL| <= 1
    "hilltop",              # 6  sS > 1 and sL >  1
)

N_CLASSES = len(CLASS_NAMES)

#: code -> name map (module constant); the inverse of enumerating CLASS_NAMES.
CODE_TO_NAME = {code: name for code, name in enumerate(CLASS_NAMES)}

#: name -> code (private helper that keeps the classifier readable).
_CODE = {name: code for code, name in enumerate(CLASS_NAMES)}

def _validate_radius(radius, label):
    """Return ``radius`` as a positive int (>= 1), else raise ``ValueError``."""
    r = int(radius)
    if r < 1:
        raise ValueError(f"{label} must be a positive integer (>= 1)")
    return r


def _box_sum(a, window):
    """Clipped moving-window sum via a summed-area table (no per-cell loop).

    For every cell: the sum of ``a`` over the odd-side ``window`` square centred
    on it, CLIPPED to the grid so only cells that exist contribute. ``a`` must
    carry 0 where a cell must not count toward the sum.
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
    """NaN-aware clipped window MEAN over a ``(2*radius+1)``-square window.

    Each cell gets the mean of the FINITE elevations in its clipped window; a
    cell whose window holds no finite elevation becomes ``nan``. Two summed-area
    tables (value sum and finite count) keep it O(N) and loop-free.
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

def _tpi(z, radius):
    """Topographic Position Index at one neighbourhood ``radius`` (Weiss 2001).

    ``z - _box_mean(z, radius)``: positive = local high, negative = local low,
    ~0 = constant-slope flank / flat. A ``nan`` input cell yields ``nan``.
    """
    return z - _box_mean(z, radius)


def _standardize(values):
    """``(values - nanmean) / nanstd`` over finite values; degenerate -> unit std.

    A constant / zero-spread field (e.g. a perfectly flat surface) is treated as
    UNIT spread so the centred values stay finite -- a flat field then
    standardises to ``0`` everywhere (read by the classifier as the middle band).
    An all-NaN field yields all ``nan``.
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

def multiscale_tpi_classes(z, dx=1.0, small_radius=2, large_radius=5):
    """Two-scale Weiss (2001) slope-position map (int8; code == CLASS_NAMES index).

    Standardises the TPI at ``small_radius`` and at ``large_radius`` to z-scores
    over the finite cells and labels every cell from the pair ``(sS, sL)`` with
    the +/-1-sigma logic in the module docstring. Returns an int8 array shaped
    like ``z`` holding one class code per cell (``0..6`` == :data:`CLASS_NAMES`
    index), and :data:`SENTINEL` (``-1``) where ``z`` is NaN or the TPI is
    otherwise undefined. ``dx`` is accepted for API symmetry but does NOT affect
    the (elevation-difference) classification. Vectorised, NaN-safe, deterministic.
    """
    rs = _validate_radius(small_radius, "small_radius")
    rl = _validate_radius(large_radius, "large_radius")
    if rl <= rs:
        raise ValueError("large_radius must be greater than small_radius")
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")

    s_small = _standardize(_tpi(z, rs))
    s_large = _standardize(_tpi(z, rl))
    valid = np.isfinite(s_small) & np.isfinite(s_large)

    s_hi = s_small > 1.0
    s_lo = s_small < -1.0
    s_mid = (s_small >= -1.0) & (s_small <= 1.0)
    l_hi = s_large > 1.0
    l_lo = s_large < -1.0
    l_mid = (s_large >= -1.0) & (s_large <= 1.0)

    code = np.full(z.shape, SENTINEL, dtype=np.int8)
    code[valid] = _CODE["flat_midslope"]                      # the "otherwise" bin
    code[valid & s_hi & l_hi] = _CODE["hilltop"]
    code[valid & s_hi & l_mid] = _CODE["upper_slope_ridge"]
    code[valid & s_lo & l_lo] = _CODE["valley"]
    code[valid & s_lo & l_mid] = _CODE["lower_slope_channel"]
    code[valid & s_mid & l_hi] = _CODE["upper_slope"]
    code[valid & s_mid & l_lo] = _CODE["lower_slope"]
    return code

def multiscale_tpi_signature(z, dx=1.0, small_radius=2, large_radius=5):
    """Compact, JSON-serialisable two-scale TPI slope-position signature.

    Classifies ``z`` with :func:`multiscale_tpi_classes` and returns::

        {"composition": {name: fraction for every name in CLASS_NAMES},
         "dominant_class": name}

    ``composition`` is the area fraction of each of the seven classes over the
    CLASSIFIED (non-sentinel) cells and sums to ~1 (all zeros for an all-NaN /
    degenerate grid). ``dominant_class`` is the class name with the largest
    fraction (ties broken toward the lower :data:`CLASS_NAMES` index), or
    ``None`` when no cell is classifiable. String-keyed, deterministic, NaN-safe.
    Carries the module claim firewall: a purely geometric two-scale
    topographic-position (nested slope-position) label -- not a geological-unit,
    process, hazard, or mission claim.
    """
    classes = multiscale_tpi_classes(z, dx=dx, small_radius=small_radius,
                                     large_radius=large_radius)
    valid = classes >= 0
    total = int(np.count_nonzero(valid))
    if total:
        counts = np.bincount(classes[valid].astype(np.int64), minlength=N_CLASSES)
    else:
        counts = np.zeros(N_CLASSES, dtype=np.int64)
    composition = {CLASS_NAMES[c]: (float(counts[c]) / total if total else 0.0)
                   for c in range(N_CLASSES)}
    if total:
        dominant = max(range(N_CLASSES), key=lambda c: counts[c])
        dominant_class = CLASS_NAMES[dominant]
    else:
        dominant_class = None
    return {"composition": composition, "dominant_class": dominant_class}
