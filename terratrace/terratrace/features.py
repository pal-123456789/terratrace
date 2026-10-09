"""Map-scale terrain morphology features.

Every feature declares its physical window and returns values whose scale
is interpretable. None of these features estimates mechanical roughness,
rock-scale obstacles, traction, or rover behaviour.
"""
from __future__ import annotations

import warnings

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view


def slope_deg(z, dx=1.0, dy=1.0):
    """Local slope magnitude in degrees from a projected elevation grid.

    For a plane z = a*x + b*y the result is arctan(sqrt(a^2+b^2)).
    """
    if dx <= 0 or dy <= 0:
        raise ValueError("dx and dy must be positive metres")
    gy, gx = np.gradient(np.asarray(z, dtype=float), dy, dx)
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def _windows(z, window):
    if window % 2 == 0:
        raise ValueError("window must be odd")
    return sliding_window_view(np.asarray(z, dtype=float), (window, window))


def relief(z, window=3, alpha=0.0):
    """Local relief = upper minus lower quantile within each window.

    alpha is the tail fraction; alpha=0 gives max-min, alpha=0.05 gives a
    robust 5th-95th percentile relief. Returns the per-window relief map.
    """
    if not 0.0 <= alpha < 0.5:
        raise ValueError("alpha must be in [0, 0.5)")
    w = _windows(z, window)
    flat = w.reshape(w.shape[0], w.shape[1], -1)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        hi = np.nanquantile(flat, 1.0 - alpha, axis=-1)
        lo = np.nanquantile(flat, alpha, axis=-1)
    return hi - lo


def ruggedness(z, window=3, dx=1.0, dy=1.0):
    """Detrended topographic ruggedness: RMS of residuals after removing a
    local best-fit plane within each window. A perfect plane returns ~0.
    """
    if window % 2 == 0:
        raise ValueError("window must be odd")
    w = _windows(z, window)
    nrow, ncol = w.shape[0], w.shape[1]
    # Local coordinates centred on the window, in metres.
    jj, ii = np.meshgrid(np.arange(window), np.arange(window))
    xx = (jj - window // 2) * dx
    yy = (ii - window // 2) * dy
    A = np.column_stack([xx.ravel(), yy.ravel(), np.ones(window * window)])
    pinv = np.linalg.pinv(A)
    out = np.full((nrow, ncol), np.nan)
    for r in range(nrow):
        block = w[r].reshape(ncol, -1)  # (ncol, window*window)
        if np.isnan(block).any():
            for c in range(ncol):
                vals = block[c]
                if np.isnan(vals).any():
                    continue
                coeffs = pinv @ vals
                resid = vals - A @ coeffs
                out[r, c] = np.sqrt(np.mean(resid ** 2))
            continue
        coeffs = (pinv @ block.T)          # (3, ncol)
        resid = block.T - A @ coeffs       # (window*window, ncol)
        out[r] = np.sqrt(np.mean(resid ** 2, axis=0))
    return out


def low_slope_connectivity(slope, threshold_deg, valid_mask=None):
    """Fraction of valid cells in the largest 4-connected component whose
    slope is at or below the threshold. A map-scale corridor statistic, not
    a route guarantee.
    """
    slope = np.asarray(slope, dtype=float)
    if valid_mask is None:
        valid_mask = ~np.isnan(slope)
    passable = valid_mask & (slope <= threshold_deg)
    n_valid = int(valid_mask.sum())
    if n_valid == 0:
        return 0.0, 0
    largest = _largest_component(passable)
    return largest / n_valid, largest


def _largest_component(mask):
    seen = np.zeros_like(mask, dtype=bool)
    rows, cols = mask.shape
    best = 0
    for sr in range(rows):
        for sc in range(cols):
            if not mask[sr, sc] or seen[sr, sc]:
                continue
            size = 0
            stack = [(sr, sc)]
            seen[sr, sc] = True
            while stack:
                r, c = stack.pop()
                size += 1
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and mask[nr, nc] and not seen[nr, nc]:
                        seen[nr, nc] = True
                        stack.append((nr, nc))
            best = max(best, size)
    return best


def aspect_dispersion(z, dx=1.0, dy=1.0):
    """Circular variance of terrain aspect in [0, 1].

    0 means a single dominant downslope direction (e.g. a planar slope);
    values near 1 mean aspect is near-isotropic. A map-scale directional
    texture summary; not a mechanical property.
    """
    if dx <= 0 or dy <= 0:
        raise ValueError("dx and dy must be positive metres")
    gy, gx = np.gradient(np.asarray(z, dtype=float), dy, dx)
    aspect = np.arctan2(gy, gx)
    finite = np.isfinite(aspect)
    if finite.sum() == 0:
        return float("nan")
    a = aspect[finite]
    r = np.hypot(np.mean(np.cos(a)), np.mean(np.sin(a)))
    return float(1.0 - r)


def hypsometric_integral(z):
    """Hypsometric integral (mean - min) / (max - min) in [0, 1].

    0.5 indicates a symmetric elevation distribution; NaN if the surface is
    flat (no relief).
    """
    v = np.asarray(z, dtype=float)
    v = v[np.isfinite(v)]
    if v.size == 0:
        return float("nan")
    lo, hi = float(np.min(v)), float(np.max(v))
    if hi - lo < 1e-12:
        return float("nan")
    return (float(np.mean(v)) - lo) / (hi - lo)
