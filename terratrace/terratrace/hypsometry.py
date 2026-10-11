"""Strahler (1952) hypsometric (area-altitude) analysis of a terrain grid.

Strahler, A.N. (1952). Hypsometric (area-altitude) analysis of erosional
topography. Geological Society of America Bulletin, 63(11), 1117-1142.

Hypsometric analysis summarises how a surface distributes its area across
elevation. Elevations are first put on a dimensionless footing by the
normalized height

    h' = (z - zmin) / (zmax - zmin)                 # in [0, 1]

over the FINITE cells only (zmin, zmax are the finite extremes). The
*hypsometric curve* gives, for every relative height ``a`` in [0, 1], the
relative AREA whose normalized height is at or above ``a`` -- the empirical
survival function ``f(a) = fraction of finite cells with h' >= a``. It is
monotonically non-increasing and runs from ``(a=0, f=1)`` to ``(a=1, f~=0)``
(only the highest cell(s) reach ``a=1``).

The *hypsometric integral* HI is the area under that curve,

    HI = integral_0^1 f(a) da = mean(h')  over finite cells,

the second equality being the "area under the survival curve equals the mean"
identity for a non-negative bounded variable. HI is a stage-of-dissection
index: ``~0.5`` is balanced ("mature"); ``> 0.5`` is top-heavy (area at HIGH
relative elevations, a "youthful", little-dissected surface); ``< 0.5`` is
bottom-heavy (area at LOW elevations, an "old", strongly dissected surface).
HI is reported directly as ``mean(h')`` so it is exact and binning-independent,
alongside the skewness and (excess) kurtosis of ``h'`` as higher-moment shape
descriptors of the same area-altitude histogram.

Degenerate case: a relief-free patch (``zmax == zmin``) has no area-altitude
structure, and is reported with integral ``0.5`` (neither top- nor
bottom-heavy), a flat curve ``f(a) == 0.5`` (whose area is exactly 0.5), and
skewness/kurtosis ``0.0``; a patch with NO finite cells returns ``nan``.

Units: ``z`` is elevation (metres); every output is DIMENSIONLESS (a normalized
height, an area fraction, or a standardized moment), so the signature does not
depend on grid spacing. Pure NumPy, NaN-safe, deterministic -- no SciPy, no
network, no disk.

Scientific boundary / claim firewall: the hypsometric integral, curve and
moments are map-scale *morphology* descriptors of the sampled grid's
area-altitude distribution ONLY. They are NOT a traversability, trafficability,
hazard, slope-stability, erosion-process, geologic-age, climate, or
mission-readiness claim; "youthful/mature/old" are Strahler's morphological
stage-of-dissection terms, not statements about absolute age or process on any
body.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "hypsometric_curve",
    "hypsometric_integral",
    "hypsometric_signature",
]


def _finite_heights(z):
    """1-D float64 array of the FINITE elevations in ``z`` (nodata dropped)."""
    v = np.asarray(z, dtype=float).ravel()
    return v[np.isfinite(v)]


def _normalized(z):
    """Classify ``z`` and return ``(status, h)``.

    ``status`` is ``"ok"`` (there is relief), ``"degenerate"`` (finite cells but
    ``zmax == zmin``), or ``"empty"`` (no finite cell). ``h`` is the 1-D array of
    normalized heights ``(z - zmin)/(zmax - zmin)`` in [0, 1] over the finite
    cells; it is meaningful only when ``status == "ok"``.
    """
    v = _finite_heights(z)
    if v.size == 0:
        return "empty", v
    zmin = float(v.min())
    zmax = float(v.max())
    rng = zmax - zmin
    if not np.isfinite(rng) or rng <= 0.0:
        return "degenerate", v
    return "ok", (v - zmin) / rng


def _shape_moments(h):
    """Standardized skewness and EXCESS kurtosis of ``h`` (population moments).

    ``skew = mean(d^3)/std^3`` and ``kurtosis = mean(d^4)/var^2 - 3`` with
    ``d = h - mean(h)`` (a Gaussian has excess kurtosis ~0). A zero-variance
    input yields ``(0.0, 0.0)`` -- a point mass has no shape.
    """
    mu = float(np.mean(h))
    d = h - mu
    var = float(np.mean(d * d))
    if not np.isfinite(var) or var <= 0.0:
        return 0.0, 0.0
    std = np.sqrt(var)
    skew = float(np.mean(d ** 3) / (std ** 3))
    kurt = float(np.mean(d ** 4) / (var * var) - 3.0)
    return skew, kurt


def hypsometric_curve(z, nbins=100):
    """Hypsometric (area-altitude) curve of ``z`` (Strahler 1952).

    Returns ``(a, area_fraction)`` as two 1-D float64 arrays of equal length
    ``nbins + 1``:

    * ``a`` -- relative heights ``linspace(0, 1, nbins + 1)``, ASCENDING;
    * ``area_fraction`` -- for each ``a`` the fraction of finite cells with
      ``h' >= a`` (the empirical survival function): monotonically
      NON-INCREASING, ``~1.0`` at ``a = 0`` and ``~0.0`` at ``a = 1``, all in
      [0, 1].

    Computed exactly from the sorted normalized heights via ``searchsorted``
    (no histogram smoothing). A relief-free grid returns the flat sentinel
    ``area_fraction == 0.5``; a grid with no finite cell returns all-``nan``
    (``a`` is unchanged in both cases). NaN-safe and deterministic.
    """
    nb = max(1, int(nbins))
    a = np.linspace(0.0, 1.0, nb + 1)
    status, h = _normalized(z)
    if status == "empty":
        return a, np.full(a.shape, np.nan)
    if status == "degenerate":
        return a, np.full(a.shape, 0.5)
    hs = np.sort(h)
    n = hs.size
    # count(h' >= a) = n - count(h' < a); integer before the divide, so the
    # result is exactly monotonically non-increasing in a.
    idx = np.searchsorted(hs, a, side="left")
    area = (n - idx) / float(n)
    return a, area


def hypsometric_integral(z):
    """Hypsometric integral of ``z`` = mean normalized height (Strahler 1952).

    ``HI = mean((z - zmin)/(zmax - zmin))`` over the FINITE cells -- the exact
    area under the hypsometric curve. Returns a plain float: ``0.5`` for a
    relief-free grid (``zmax == zmin``) and ``nan`` for a grid with no finite
    cell. NaN-safe (nodata ignored) and binning-independent.
    """
    status, h = _normalized(z)
    if status == "empty":
        return float("nan")
    if status == "degenerate":
        return 0.5
    return float(np.mean(h))


def hypsometric_signature(z):
    """Compact, JSON-serialisable hypsometric signature of ``z`` (Strahler 1952).

    Reduces the area-altitude distribution to plain Python floats::

        {"integral": float,     # hypsometric integral = mean normalized height
         "skew":     float,     # skewness of h' (standardized 3rd moment)
         "kurtosis": float,     # EXCESS kurtosis of h' (4th moment - 3)
         "curve":    [f0..f10]} # 11 area fractions at a = 0.0, 0.1, ..., 1.0

    ``curve`` is :func:`hypsometric_curve` on the fixed decile grid (``nbins=10``
    -> ``a = 0.0, 0.1, ..., 1.0``). A relief-free grid gives integral ``0.5``,
    ``skew``/``kurtosis`` ``0.0`` and a flat ``curve`` of 0.5; a grid with no
    finite cell gives ``nan`` integral/skew/kurtosis and an all-``nan`` curve.
    Deterministic. Carries the module's claim firewall: map-scale area-altitude
    morphology only -- not a traversability, hazard, geologic-age, process, or
    mission claim.
    """
    status, h = _normalized(z)
    _a, area = hypsometric_curve(z, nbins=10)   # a = 0.0, 0.1, ..., 1.0 (11 pts)
    curve = [float(x) for x in area]
    if status == "empty":
        nan = float("nan")
        return {"integral": nan, "skew": nan, "kurtosis": nan, "curve": curve}
    if status == "degenerate":
        return {"integral": 0.5, "skew": 0.0, "kurtosis": 0.0, "curve": curve}
    skew, kurt = _shape_moments(h)
    return {"integral": float(np.mean(h)), "skew": skew,
            "kurtosis": kurt, "curve": curve}
