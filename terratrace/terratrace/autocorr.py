"""Spatial autocorrelation of an elevation field: correlation-vs-lag and a
data-driven block size for the spatial bootstrap.

DEM pixels are not independent: nearby cells carry similar elevation, so a
moving-block bootstrap (``uncertainty.block_bootstrap_pareto``) needs a block
size at or above the terrain's *correlation length* for its confidence
intervals to be honest. Choosing that block by eye is unprincipled. This module
measures how fast the field decorrelates with lag and turns that into a single
correlation length (and a clamped block size) so the choice is made from the
data instead.

Claim firewall (inherited from the feature layer): the autocorrelation curve
and correlation length are map-scale descriptive statistics of the elevation
grid only. They say how spatially smooth the sampled surface is; they do NOT
estimate traversability, mechanical roughness, traction, rock-scale obstacles,
or rover / mission behaviour.
"""
from __future__ import annotations

import numpy as np


def _lag_corr(field, h):
    """Pearson correlation of ``field`` with itself shifted by ``h`` pixels,
    pooling the x-shift and the y-shift over finite pairs only.

    Returns the correlation as a float, or ``None`` when fewer than two finite
    pairs exist or either side has zero variance (an undefined correlation).
    """
    ax = field[:, h:].ravel()
    bx = field[:, :-h].ravel()
    ay = field[h:, :].ravel()
    by = field[:-h, :].ravel()
    a = np.concatenate([ax, ay])
    b = np.concatenate([bx, by])
    mask = np.isfinite(a) & np.isfinite(b)
    a = a[mask]
    b = b[mask]
    if a.size < 2:
        return None
    am = a - a.mean()
    bm = b - b.mean()
    denom = np.sqrt(np.sum(am * am) * np.sum(bm * bm))
    if denom <= 0.0:
        return None
    return float(np.sum(am * bm) / denom)


def autocorrelation_curve(field, max_lag=20, dx=1.0):
    """Spatial autocorrelation of ``field`` against lag.

    For each integer lag ``h`` in ``1..max_lag`` (capped at ``min(shape)-1``)
    the Pearson correlation between the field and itself shifted by ``h`` is
    computed, pooling the x-shift (``field[:, h:]`` vs ``field[:, :-h]``) and the
    y-shift (``field[h:, :]`` vs ``field[:-h, :]``) over finite pairs only. Lag 0
    is included as the exact value 1.0. A lag with fewer than two valid pairs or
    zero variance is skipped.

    Returns ``{lag_metres: correlation}`` with ``lag_metres = h * dx`` and
    correlation in ``[-1, 1]`` (NaN-aware).
    """
    f = np.asarray(field, dtype=float)
    if f.ndim != 2:
        raise ValueError("autocorrelation_curve needs a 2-D field")
    eff = min(int(max_lag), min(f.shape) - 1)
    curve = {0.0: 1.0}
    for h in range(1, eff + 1):
        r = _lag_corr(f, h)
        if r is None:
            continue
        curve[float(h * dx)] = r
    return curve


def correlation_length(field, max_lag=20, dx=1.0, threshold=None):
    """Lag at which the autocorrelation first drops to/below ``threshold``.

    ``threshold`` defaults to ``1/e`` (~0.3679), the usual e-folding definition
    of a correlation length. Returns a dict with ``length_px`` (int, the smallest
    lag in pixels whose correlation is at or below the threshold; if none within
    the examined range, the examined ceiling ``min(max_lag, min(shape)-1)``),
    ``length_m = length_px * dx``, the resolved ``threshold``, and the ``curve``.
    """
    if threshold is None:
        threshold = 1.0 / np.e
    threshold = float(threshold)
    f = np.asarray(field, dtype=float)
    curve = autocorrelation_curve(f, max_lag=max_lag, dx=dx)
    eff = min(int(max_lag), min(f.shape) - 1)
    length_px = eff
    for h in range(1, eff + 1):
        key = float(h * dx)
        if key in curve and curve[key] <= threshold:
            length_px = h
            break
    length_px = int(length_px)
    return {
        "length_px": length_px,
        "length_m": float(length_px * dx),
        "threshold": threshold,
        "curve": curve,
    }


def suggest_block_size(field, min_block=2, max_block=16, max_lag=20, dx=1.0):
    """Data-driven moving-block size: the correlation length in PIXELS, clamped
    to ``[min_block, max_block]``.

    Feed the returned int to ``uncertainty.block_bootstrap_pareto``'s ``block``
    argument so the spatial bootstrap resamples blocks at or above the terrain's
    correlation length (honest, autocorrelation-aware confidence intervals)
    instead of near-independent pixels (optimistically narrow intervals).
    """
    length_px = correlation_length(field, max_lag=max_lag, dx=dx)["length_px"]
    lo, hi = int(min_block), int(max_block)
    return int(min(hi, max(lo, length_px)))
