"""Matheron (1963) empirical semivariogram -- the geostatistical second-order
structure signature of a surface.

Matheron, G. (1963). Principles of geostatistics. Economic Geology 58(8),
1246-1266.

The empirical semivariogram summarises how the squared height difference between
two samples grows with their separation ``h`` (the "lag"):

    gamma(h) = 0.5 * mean( (z(x) - z(x + h))^2 )      over all finite pairs

A small ``gamma`` at short lags that climbs to a plateau ("sill") at some lag
("range") is the classic signature of a spatially autocorrelated field: nearby
samples resemble one another up to the range, beyond which they are effectively
uncorrelated. A field with no spatial structure (white noise) has a FLAT
semivariogram pinned at the sill from the very first lag -- all of its variance
is "nugget".

Estimation (axis-shifted differences). For each integer pixel lag ``k`` in
``1..n_lags`` this module forms the shifted differences along each grid axis,

    x-lag:  z[:, k:] - z[:, :-k]        y-lag:  z[k:, :] - z[:-k, :]

takes ``0.5 * nanmean(diff**2)`` of each (the directional semivariance over all
finite pairs) and reports the OMNIDIRECTIONAL semivariance as the mean of the x-
and y-directional values at that lag. The lag in metres is ``k * dx``.

The signature condenses the curve into five plain floats::

    {"sill":               finite variance of z (the plateau level),
     "nugget":             intercept at h->0 of a least-squares line through the
                           first ~3 lags of gamma, clamped to >= 0,
     "range_m":            smallest lag (m) with gamma >= 0.95*sill, else the
                           largest lag,
     "vario_loglog_slope": slope of log(gamma) vs log(h) over the RISING part
                           (lags before range); nan with < 2 usable points,
     "aniso_ratio":        max(range_x, range_y)/min(range_x, range_y) >= 1 from
                           separate x-only and y-only variograms (1.0 =
                           isotropic); nan if a directional range is undefined}

Degenerate inputs yield ``nan`` for the affected field (no finite samples -> all
nan; a flat or sub-range-only curve -> nan ``vario_loglog_slope``). Pure NumPy,
NaN-safe (nodata cells drop out of every ``nanmean``/``nanvar``), deterministic
-- no SciPy, no network, no disk.
Scientific boundary / claim firewall: this is a geostatistical second-order
structure summary (semivariance) of the sampled height field. The ``range``
relates to the terrain autocorrelation length and ``vario_loglog_slope`` to its
roughness scaling. It is map-scale MORPHOLOGY only -- no process,
traversability, habitability or mission claim on Mars, the Moon, Mercury, Ceres,
Earth or any other body. "Sill", "nugget", "range" and "anisotropy" are used in
their abstract geostatistical sense and carry no geological-process meaning here.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "semivariogram",
    "variogram_signature",
]


def _dir_semivariance(z, k, axis):
    """Directional semivariance ``0.5*nanmean(diff**2)`` at integer lag ``k``.

    ``axis=1`` shifts along columns (the x direction), ``axis=0`` along rows (the
    y direction). NaN pairs drop out of the ``nanmean``; returns ``nan`` when no
    finite pair exists at this lag/axis (never raises).
    """
    if axis == 1:
        diff = z[:, k:] - z[:, :-k]
    else:
        diff = z[k:, :] - z[:-k, :]
    sq = diff * diff
    if not np.any(np.isfinite(sq)):
        return float("nan")
    return 0.5 * float(np.nanmean(sq))


def _directional_variogram(z, dx, n_lags, axis):
    """``(lags_m, gamma)`` along a single axis; ``gamma`` is ``nan`` where the
    lag does not fit the array along ``axis`` or has no finite pair."""
    nmax = max(1, int(n_lags))
    lags = np.arange(1, nmax + 1, dtype=float) * float(dx)
    gamma = np.full(nmax, np.nan, dtype=float)
    if z.ndim != 2:
        return lags, gamma
    dim = z.shape[axis]
    for i, k in enumerate(range(1, nmax + 1)):
        if dim > k:
            gamma[i] = _dir_semivariance(z, k, axis)
    return lags, gamma


def _ls_line(x, y):
    """Least-squares ``(slope, intercept)`` of ``y ~ slope*x + intercept``.

    Returns ``(nan, nan)`` with fewer than two points or zero x-variance.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 2:
        return float("nan"), float("nan")
    xm = float(x.mean())
    ym = float(y.mean())
    dxv = x - xm
    sxx = float(np.sum(dxv * dxv))
    if sxx <= 1e-15:
        return float("nan"), float("nan")
    slope = float(np.sum(dxv * (y - ym)) / sxx)
    intercept = float(ym - slope * xm)
    return slope, intercept


def _range_from(lags, gamma, thresh):
    """Smallest finite lag with ``gamma >= thresh``; else the largest finite
    lag; ``nan`` if no finite gamma exists."""
    mask = np.isfinite(lags) & np.isfinite(gamma)
    L = lags[mask]
    G = gamma[mask]
    if L.size == 0:
        return float("nan")
    hits = L[G >= thresh]
    if hits.size > 0:
        return float(np.min(hits))
    return float(np.max(L))


def semivariogram(z, dx=1.0, n_lags=12):
    """Omnidirectional empirical semivariogram of ``z`` (Matheron 1963).

    Returns two 1-D float64 arrays ``(lags_m, gamma)`` of length ``n_lags``: the
    lag in metres (``k*dx`` for ``k = 1..n_lags``) and the omnidirectional
    semivariance -- the mean of the x-shift and y-shift directional semivariance
    at each lag. ``gamma`` is ``nan`` at any lag with no finite pair (e.g. a lag
    larger than the array). NaN-safe (``nanmean`` over finite pairs) and
    deterministic.
    """
    z = np.asarray(z, dtype=float)
    lags, gx = _directional_variogram(z, dx, n_lags, axis=1)
    _, gy = _directional_variogram(z, dx, n_lags, axis=0)
    stack = np.vstack([gx, gy])
    gamma = np.full(lags.shape, np.nan, dtype=float)
    colmask = np.any(np.isfinite(stack), axis=0)
    if np.any(colmask):
        gamma[colmask] = np.nanmean(stack[:, colmask], axis=0)
    return lags, gamma

def variogram_signature(z, dx=1.0, n_lags=12):
    """Five-number geostatistical structure signature of ``z`` (Matheron 1963).

    Returns a compact, JSON-serialisable dict::

        {"sill": float,               # finite variance of z (plateau level)
         "nugget": float,             # intercept at h->0, clamped to >= 0
         "range_m": float,            # smallest lag (m) with gamma >= 0.95*sill
         "vario_loglog_slope": float, # log-log roughness slope over rising part
         "aniso_ratio": float}        # directional range ratio >= 1 (1 = isotropic)

    Values are plain floats, ``nan`` where undefined, deterministic across calls.
    NaN-safe: nodata cells drop out of every ``nanmean``/``nanvar`` and nothing
    raises. Carries the module claim firewall -- a map-scale morphology summary,
    not a process/traversability/mission claim on any body.
    """
    nan = float("nan")
    out = {"sill": nan, "nugget": nan, "range_m": nan,
           "vario_loglog_slope": nan, "aniso_ratio": nan}

    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if np.any(np.isfinite(z)):
        out["sill"] = float(np.nanvar(z))
    sill = out["sill"]

    lags, gamma = semivariogram(z, dx=dx, n_lags=n_lags)
    mask = np.isfinite(lags) & np.isfinite(gamma)
    L = lags[mask]
    G = gamma[mask]
    if not np.isfinite(sill) or L.size == 0:
        return out

    # nugget: intercept of a LS line through the first ~3 lags, clamped to >= 0.
    k_fit = int(min(3, L.size))
    _, intercept = _ls_line(L[:k_fit], G[:k_fit])
    if np.isfinite(intercept):
        out["nugget"] = float(max(0.0, intercept))

    # range: smallest lag reaching 95% of the sill, else the largest lag.
    thresh = 0.95 * sill
    out["range_m"] = _range_from(lags, gamma, thresh)

    # roughness scaling: slope of log(gamma) vs log(h) over the rising part
    # (lags strictly before the range), using only positive, finite samples.
    rng_m = out["range_m"]
    rising = (L < rng_m) if np.isfinite(rng_m) else np.ones(L.size, dtype=bool)
    pos = rising & (G > 0.0) & (L > 0.0)
    if int(np.count_nonzero(pos)) >= 2:
        slope_ll, _ = _ls_line(np.log(L[pos]), np.log(G[pos]))
        if np.isfinite(slope_ll):
            out["vario_loglog_slope"] = float(slope_ll)

    # anisotropy: ratio of directional ranges from x-only and y-only variograms.
    lx, gxx = _directional_variogram(z, dx, n_lags, axis=1)
    ly, gyy = _directional_variogram(z, dx, n_lags, axis=0)
    range_x = _range_from(lx, gxx, thresh)
    range_y = _range_from(ly, gyy, thresh)
    if np.isfinite(range_x) and np.isfinite(range_y):
        lo = min(range_x, range_y)
        hi = max(range_x, range_y)
        if lo > 0.0:
            out["aniso_ratio"] = float(hi / lo)

    return out
