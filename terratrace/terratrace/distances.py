"""Distribution distances for terrain-feature comparison.

Implemented without SciPy so the engine stays dependency-light. All
functions ignore NaN values and operate on 1-D samples.
"""
from __future__ import annotations

import numpy as np

_QGRID = np.linspace(0.0, 1.0, 201)


def _clean(x):
    x = np.asarray(x, dtype=float).ravel()
    return x[np.isfinite(x)]


def wasserstein1(x, y, qgrid=_QGRID):
    """Approximate 1-D Wasserstein-1 distance via quantile integration.

    For Y = X + c this returns |c|. Uses an explicit trapezoid rule so it
    is independent of np.trapz/np.trapezoid (which changed across NumPy
    versions).
    """
    x, y = _clean(x), _clean(y)
    if x.size == 0 or y.size == 0:
        return float("nan")
    qx = np.quantile(x, qgrid)
    qy = np.quantile(y, qgrid)
    diff = np.abs(qx - qy)
    return float(np.sum(0.5 * (diff[1:] + diff[:-1]) * np.diff(qgrid)))


def ks_distance(x, y):
    """Kolmogorov-Smirnov distance: sup |F_x - F_y| in [0, 1]."""
    x, y = np.sort(_clean(x)), np.sort(_clean(y))
    if x.size == 0 or y.size == 0:
        return float("nan")
    grid = np.concatenate([x, y])
    grid.sort()
    fx = np.searchsorted(x, grid, side="right") / x.size
    fy = np.searchsorted(y, grid, side="right") / y.size
    return float(np.max(np.abs(fx - fy)))


def quantile_fingerprint(x, probs=(0.05, 0.25, 0.5, 0.75, 0.95)):
    x = _clean(x)
    if x.size == 0:
        return {str(p): float("nan") for p in probs}
    return {str(p): float(np.quantile(x, p)) for p in probs}


def normalized_distance(x, y, scale=None):
    """Wasserstein-1 normalized by a declared scale.

    Default scale is the pooled IQR, with a std -> range fallback so that
    flat/filled tiles (zero IQR but non-zero spread) do not blow up. If the
    pooled sample is genuinely constant the distance is 0.
    """
    xc, yc = _clean(x), _clean(y)
    if xc.size == 0 or yc.size == 0:
        return float("nan")
    w = wasserstein1(xc, yc)
    if scale is None:
        pooled = np.concatenate([xc, yc])
        scale = np.quantile(pooled, 0.75) - np.quantile(pooled, 0.25)
        if not np.isfinite(scale) or scale <= 1e-9:
            scale = float(np.std(pooled))
        if not np.isfinite(scale) or scale <= 1e-9:
            scale = float(np.max(pooled) - np.min(pooled))
    if not np.isfinite(scale) or scale <= 1e-9:
        return 0.0 if w <= 1e-12 else 1.0
    return w / scale
