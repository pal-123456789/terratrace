"""Flint (1974) slope-area scaling -- the concavity signature of a surface.

Flint, J.J. (1974). Stream gradient as a function of order, magnitude, and
discharge. Water Resources Research 10(5), 969-973.

The slope-area relation is the classic power law linking local gradient to the
upslope contributing (drainage) area that routes through a cell:

    S = ks * A^(-theta)        <=>        log10(S) = log10(ks) - theta*log10(A)

where ``S`` is the local slope (here the tangent of the surface gradient, i.e.
the magnitude of ``grad z``), ``A`` is the upslope contributing area, ``theta``
is the *concavity index* and ``ks`` the *steepness coefficient*. A surface whose
gradient FLATTENS as more area drains through it (a concave down-area profile)
has ``theta > 0``; a surface whose slope is independent of area has ``theta ~ 0``.

Estimation (robust, binning-based). Per finite cell this module takes

    S = |grad z|                     from ``np.gradient(z, dx, dx)``  (tan slope)
    A = flow_accumulation(z) * dx^2  in m^2    # REUSES the engine's D8 routing

over cells with finite, positive ``S`` and ``A``, bins them into ~12 equal-width
bins in ``log10(A)``, takes the MEDIAN ``log10(S)`` per non-empty bin, and does a
least-squares fit of those bin medians versus ``log10(A)``. Then
``flint_theta = -slope``, ``log_ks = intercept`` and ``r2`` is the fit's
coefficient of determination. Median-of-bin fitting (rather than fitting the raw
cloud) is the standard way to keep the estimate from being dominated by the many
small-area cells that crowd the low end of the slope-area scatter.

Degenerate inputs -> ``flint_theta = nan``: fewer than two non-empty bins, a
single contributing-area value (no area variance to regress against), or a
CONSTANT slope (zero slope variance -- slope independent of area, so the Flint
relation is undefined). ``n_bins_used`` is still reported in those cases.

Units: ``dx`` is grid spacing in metres; ``A`` is in m^2 and ``S`` is
dimensionless (a tangent). ``theta`` and ``r2`` are dimensionless. Pure NumPy,
NaN-safe (nodata cells and their gradient neighbours are dropped), deterministic
-- no SciPy, no network, no disk.

Scientific boundary / claim firewall: this is a purely GEOMETRIC
slope-versus-contributing-area scaling of the sampled height field. It is NOT a
claim of fluvial processes, running water, precipitation, climate, erosion
history, landscape age, or any surface/hydrological process on Mars, the Moon,
Mercury, Ceres, Earth or any other body. "Slope", "area", "concavity" and
"steepness" are used in their abstract grid-geometry sense; ``A`` is a
space-filling flow-accumulation area on a depression-filled grid, exactly as the
flow-accumulation operator is defined in geomorphometry, and carries no
hydrological meaning here.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "slope_area_arrays",
    "slope_area_signature",
]

def _slope_field(z, dx):
    """Tangent-slope field ``|grad z|`` from ``np.gradient(z, dx, dx)``.

    Returns a float64 array shaped like ``z``; NaN cells (and the immediate
    gradient neighbours they contaminate) carry NaN. ``S`` is the magnitude of
    the elevation gradient -- the tangent of the surface slope angle.
    """
    gy, gx = np.gradient(z, dx, dx)
    return np.hypot(gx, gy)


def slope_area_arrays(z, dx=1.0):
    """Flattened ``(area, slope)`` pairs over finite cells (Flint 1974 inputs).

    Returns two equal-length 1-D float64 arrays ``(area, slope)``:

    * ``area``  -- upslope contributing area ``flow_accumulation(z) * dx^2`` in
      m^2, strictly ``> 0`` on every returned cell (D8 accumulation is ``>= 1``);
    * ``slope`` -- the tangent slope ``|grad z|`` (dimensionless), ``>= 0``.

    Only cells with finite ``area`` and ``slope`` are kept, so nodata (NaN) cells
    and the gradient neighbours they contaminate are dropped (NaN-safe, never
    raises). The D8 flow accumulation is imported lazily from
    :mod:`terratrace.drainage` so importing this module stays cheap.
    """
    from terratrace import drainage

    z = np.asarray(z, dtype=float)
    dx = float(dx)
    if z.ndim != 2 or z.shape[0] < 2 or z.shape[1] < 2 or dx <= 0.0:
        empty = np.empty(0, dtype=float)
        return empty, empty.copy()
    slope = _slope_field(z, dx)
    area = drainage.flow_accumulation(z) * dx * dx
    mask = np.isfinite(area) & np.isfinite(slope) & (area > 0.0) & (slope >= 0.0)
    return area[mask], slope[mask]


def slope_area_signature(z, dx=1.0, nbins=12):
    """Flint (1974) slope-area concavity signature of ``z``.

    Builds the finite ``(area, slope)`` cloud with :func:`slope_area_arrays`,
    restricts to strictly-positive-slope cells (needed for ``log10``), bins them
    into ``nbins`` equal-width ``log10(area)`` bins, takes the MEDIAN
    ``log10(slope)`` per non-empty bin and least-squares fits those bin medians
    against ``log10(area)``. Returns a compact, JSON-serialisable dict::

        {"flint_theta": float,   # concavity index  = -slope of the log-log fit
         "r2":          float,   # fit coefficient of determination in [0, 1]
         "log_ks":      float,   # intercept = log10(ks), the steepness coeff.
         "n_bins_used": int}     # number of non-empty bins entering the fit

    A concave surface (slope flattening as area grows) gives ``flint_theta > 0``.
    Degenerate inputs (``n_bins_used < 2``, a single contributing-area value, or a
    constant slope with no variance to regress) yield ``flint_theta``/``r2``/
    ``log_ks`` of ``nan`` while still reporting ``n_bins_used``. Deterministic and
    NaN-safe. Carries the module's claim firewall: a purely geometric slope-area
    scaling of the surface, NOT a fluvial/water/erosion claim on any body.
    """
    nan = float("nan")
    out = {"flint_theta": nan, "r2": nan, "log_ks": nan, "n_bins_used": 0}

    area, slope = slope_area_arrays(z, dx=dx)
    pos = slope > 0.0
    area = area[pos]
    slope = slope[pos]
    if area.size < 2:
        return out

    log_a = np.log10(area)
    log_s = np.log10(slope)
    a_lo = float(log_a.min())
    a_hi = float(log_a.max())
    if not np.isfinite(a_lo) or not np.isfinite(a_hi) or a_hi <= a_lo:
        out["n_bins_used"] = 1          # all area in a single bin -> degenerate
        return out

    nb = max(2, int(nbins))
    edges = np.linspace(a_lo, a_hi, nb + 1)
    which = np.digitize(log_a, edges[1:-1])     # bin index in 0..nb-1
    xb = []
    yb = []
    for b in range(nb):
        sel = which == b
        if np.any(sel):
            xb.append(float(np.median(log_a[sel])))
            yb.append(float(np.median(log_s[sel])))
    x = np.asarray(xb, dtype=float)
    y = np.asarray(yb, dtype=float)
    out["n_bins_used"] = int(x.size)
    if x.size < 2:
        return out
    xm = float(x.mean())
    ym = float(y.mean())
    dxv = x - xm
    dyv = y - ym
    sxx = float(np.sum(dxv * dxv))
    syy = float(np.sum(dyv * dyv))
    sxy = float(np.sum(dxv * dyv))
    eps = 1e-12
    if sxx <= eps or syy <= eps:
        # no area variance (cannot fit a line) or no slope variance (constant
        # slope -> slope independent of area): the Flint relation is undefined.
        return out

    slope_fit = sxy / sxx
    intercept = ym - slope_fit * xm
    r2 = (sxy * sxy) / (sxx * syy)
    out["flint_theta"] = float(-slope_fit)
    out["r2"] = float(min(1.0, max(0.0, r2)))
    out["log_ks"] = float(intercept)
    return out
