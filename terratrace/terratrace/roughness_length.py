"""Shepard et al. (2001) RMS-deviation (Allan-deviation) roughness of a surface.

Shepard, M.K., Campbell, B.A., Bulmer, M.H., Farr, T.G., Gaddis, L.R. &
Plaut, J.J. (2001). The roughness of natural terrain: A planetary and remote
sensing perspective. Journal of Geophysical Research 106(E12), 32777-32795.

Shepard et al. characterise natural-terrain roughness by the RMS deviation
(a.k.a. the Allan deviation) of the height field versus horizontal lag Dx:

    nu(Dx) = sqrt( < ( z(x + Dx) - z(x) ) ** 2 > )

the root-mean-square of the elevation DIFFERENCE across a step of Dx. For a
self-affine surface it follows a power law nu(Dx) = nu0 * Dx ** H, where H is
the Hurst (roughness) exponent: H -> 1 is smooth / long-correlated (the
difference keeps growing with lag, as on a tilted ramp) and H -> 0 is rough /
decorrelated (the difference saturates at once, as for white noise). A log-log
plot of nu against Dx is the *deviogram*; its slope is the deviogram Hurst.

This module reports a compact four-number summary of that curve::

    rms_height          std of the DETRENDED height field (best-fit plane out)
    rms_slope           RMS of the gradient magnitude |grad z| (a tangent slope)
    hurst_deviogram     slope of log nu vs log Dx, clamped to [0, 1.5]
    roughness_length_m  e-folding decorrelation lag of the difference field

The e-folding roughness length is the smallest lag at which nu reaches
(1 - 1/e) of its value at the largest sampled lag -- a decorrelation length of
the height-difference field, in metres.

Units: dx is grid spacing in metres; rms_height is in elevation units,
rms_slope is dimensionless (a tangent), hurst_deviogram is dimensionless and
roughness_length_m is in metres. Pure NumPy, NaN-safe (non-finite cells are
dropped from every reduction and nothing raises) and deterministic -- no SciPy,
no network, no disk.

Scientific boundary / claim firewall: this is an RMS-deviation (Allan-deviation)
roughness summary of the height field, closely related to the structure function
and Hurst scaling already in the engine; map-scale morphology only; not a
radar-backscatter, trafficability, or mission claim.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "rms_deviation_profile",
    "roughness_length_signature",
]


def rms_deviation_profile(z, dx=1.0, n_lags=12):
    """RMS-deviation (Allan-deviation) profile nu(Dx) of a height field.

    Returns two equal-length 1-D float64 arrays ``(lags_m, nu)``. For each
    integer pixel lag ``k = 1 .. n_lags`` (capped at ``min(z.shape) - 1``),
    ``lags_m = k * dx`` in metres and ``nu`` is the root-mean-square of the
    elevation differences at that lag, POOLING the x- and y-direction steps so
    the estimate is isotropic (the structure-function convention already used in
    :mod:`terratrace.features`). Only finite differences enter each mean, so
    nodata (NaN) cells are dropped (NaN-safe, never raises) and a lag whose
    differences are entirely non-finite is omitted. Degenerate inputs (not 2-D,
    fewer than two rows/cols, or ``dx <= 0``) return two empty arrays.
    Deterministic, pure NumPy.
    """
    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if z.ndim != 2 or z.shape[0] < 2 or z.shape[1] < 2 or dx <= 0.0:
        empty = np.empty(0, dtype=float)
        return empty, empty.copy()
    max_lag = min(int(n_lags), min(z.shape) - 1)
    lags = []
    nus = []
    for k in range(1, max_lag + 1):
        dxdiff = z[:, k:] - z[:, :-k]
        dydiff = z[k:, :] - z[:-k, :]
        pooled = np.concatenate([dxdiff.ravel(), dydiff.ravel()])
        pooled = pooled[np.isfinite(pooled)]
        if pooled.size == 0:
            continue
        lags.append(float(k * dx))
        nus.append(float(np.sqrt(np.mean(pooled ** 2))))
    return np.asarray(lags, dtype=float), np.asarray(nus, dtype=float)


def _detrended_std(z):
    """Std of ``z`` after removing the least-squares best-fit plane.

    Falls back to the raw std of the finite values when a plane is
    under-determined (not 2-D, fewer than three finite cells, or finite cells
    that do not span two dimensions) -- the documented degenerate behaviour.
    """
    z = np.asarray(z, dtype=float)
    finite = np.isfinite(z)
    v = z[finite]
    n = v.size
    if n == 0:
        return float("nan")
    if z.ndim != 2 or n < 3:
        return float(np.std(v))
    yy, xx = np.nonzero(finite)
    A = np.column_stack([xx.astype(float), yy.astype(float), np.ones(n)])
    if np.linalg.matrix_rank(A) < 3:
        return float(np.std(v))
    coeffs, *_ = np.linalg.lstsq(A, v, rcond=None)
    resid = v - A @ coeffs
    if not np.all(np.isfinite(resid)):
        return float(np.std(v))
    return float(np.std(resid))


def _rms_slope(z, dx):
    """RMS of the gradient magnitude ``|grad z|`` (a dimensionless tangent)."""
    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if z.ndim != 2 or z.shape[0] < 2 or z.shape[1] < 2 or dx <= 0.0:
        return float("nan")
    gy, gx = np.gradient(z, dx, dx)
    mag = np.hypot(gx, gy)
    mag = mag[np.isfinite(mag)]
    if mag.size == 0:
        return float("nan")
    return float(np.sqrt(np.mean(mag ** 2)))


def roughness_length_signature(z, dx=1.0, n_lags=12):
    """Shepard et al. (2001) RMS-deviation roughness signature of ``z``.

    Returns a compact, JSON-serialisable dict of plain floats (``nan`` where a
    quantity is undefined)::

        {"rms_height":         float,  # std of the detrended height field
         "rms_slope":          float,  # RMS gradient magnitude (tangent slope)
         "hurst_deviogram":    float,  # slope of log nu vs log Dx in [0, 1.5]
         "roughness_length_m": float}  # e-folding lag of the difference field

    ``hurst_deviogram`` is the least-squares slope of ``log nu`` versus
    ``log Dx`` over the usable lags (finite, ``nu > 0``), clamped to ``[0, 1.5]``
    and ``nan`` with fewer than two usable lags. ``roughness_length_m`` is the
    smallest lag at which ``nu`` reaches ``(1 - 1/e)`` of its largest-lag value
    (the saturation), or the largest lag if that level is never reached.
    Deterministic and NaN-safe. Carries the module claim firewall: an
    Allan-deviation roughness summary of the height field, map-scale morphology
    only -- not a radar, trafficability or mission claim.
    """
    nan = float("nan")
    out = {
        "rms_height": nan,
        "rms_slope": nan,
        "hurst_deviogram": nan,
        "roughness_length_m": nan,
    }
    z = np.asarray(z, dtype=float)
    dx = float(dx)
    out["rms_height"] = _detrended_std(z)
    out["rms_slope"] = _rms_slope(z, dx)
    lags_m, nu = rms_deviation_profile(z, dx=dx, n_lags=n_lags)
    usable = np.isfinite(lags_m) & np.isfinite(nu) & (lags_m > 0.0) & (nu > 1e-12)
    lx = np.log(lags_m[usable])
    ly = np.log(nu[usable])
    if lx.size >= 2 and float(np.sum((lx - lx.mean()) ** 2)) > 1e-12:
        slope = float(np.polyfit(lx, ly, 1)[0])
        out["hurst_deviogram"] = float(min(1.5, max(0.0, slope)))
    fin = np.isfinite(lags_m) & np.isfinite(nu)
    L = lags_m[fin]
    V = nu[fin]
    if L.size:
        saturation = float(V[-1])
        if np.isfinite(saturation):
            threshold = (1.0 - 1.0 / np.e) * saturation
            reached = V >= threshold
            idx = int(np.argmax(reached)) if np.any(reached) else L.size - 1
            out["roughness_length_m"] = float(L[idx])
    return out
