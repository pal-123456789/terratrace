"""Shannon (1948) information entropy of terrain distributions (pure NumPy).

Shannon, C.E. (1948). A mathematical theory of communication. Bell System
Technical Journal, 27(3), 379-423 (and 27(4), 623-656).

A terrain-complexity / diversity descriptor. The Shannon entropy of a
normalized histogram,

    H = -sum_i p_i * log2(p_i)        (bits; the bins with p_i = 0 are skipped),

measures how evenly a quantity's probability mass is spread across its bins.
``H = 0`` when every sample falls in one bin (a single, perfectly ordered
value); ``H`` is maximal, ``log2(nbins)`` bits, when the ``nbins`` bins are
equally populated (a maximally diverse / uniform distribution). This module
reports ``H`` for two distributions of a projected elevation grid:

* the SLOPE distribution -- local slope magnitude in DEGREES, computed from
  ``np.gradient`` at grid spacing ``dx`` as ``degrees(arctan(hypot(dz/dx,
  dz/dy)))`` (the same convention as :mod:`terratrace.features`), histogrammed
  with ``nbins`` bins over ``[0, max_slope]``; and
* the ELEVATION distribution -- height put on a dimensionless [0, 1] footing by
  ``(z - zmin)/(zmax - zmin)`` over the FINITE cells, histogrammed with
  ``nbins`` bins over ``[0, 1]``.

Alongside each raw entropy (bits) it reports the NORMALIZED entropy
``H / log2(nbins)`` in [0, 1]: ``1.0`` is a maximally diverse (uniform)
histogram, ``0.0`` is all mass in a single bin. A relief-free (constant) grid
has zero slope everywhere, hence slope entropy -- and normalized slope entropy
-- of exactly ``0.0``; a single planar ramp has one constant slope value, so
likewise ``0.0``.

NaN policy: non-finite cells are IGNORED. Slopes are formed on the raw grid and
only the finite slope values are histogrammed, so nodata never raises and every
output is finite. Pure NumPy, deterministic -- no SciPy, no network, no disk.

Scientific boundary / claim firewall: these are MAP-SCALE MORPHOLOGY /
information-content descriptors of the sampled grid's slope and elevation
distributions ONLY -- how diverse (spread) those distributions are. They are
NOT a traversability, trafficability, hazard, slope-stability, geologic-origin,
resource, climate, or mission-readiness claim, and say nothing about rock-scale
structure below the pixel scale.
"""
from __future__ import annotations

import numpy as np

__all__ = ["shannon_entropy", "entropy_signature"]


def _slope_degrees(z, dx):
    """Local slope magnitude in degrees via ``np.gradient`` at spacing ``dx``.

    ``degrees(arctan(hypot(dz/dx, dz/dy)))`` with the same ``dx`` spacing on both
    axes -- the convention of :func:`terratrace.features.slope_deg`. Non-finite
    cells propagate NaN into their neighbourhood; the caller drops those before
    histogramming.
    """
    za = np.asarray(z, dtype=float)
    gy, gx = np.gradient(za, float(dx))
    return np.degrees(np.arctan(np.hypot(gx, gy)))


def shannon_entropy(values, nbins=64, vmin=None, vmax=None):
    """Shannon entropy (bits) of ``values`` over a ``nbins`` normalized histogram.

    Flattens ``values``, drops non-finite entries, histograms the remainder with
    ``nbins`` equal-width bins over ``[vmin, vmax]`` (the finite data min/max when
    either bound is ``None``), normalizes the counts to a probability mass
    function and returns ``H = -sum(p * log2(p))`` over the NON-EMPTY bins only.

    NaN-safe and degeneracy-safe: returns ``0.0`` (plain float) when there is no
    finite sample, when ``vmax <= vmin`` (no spread -> all mass in one bin), or
    when every sample lands in a single bin. The result is in bits and ``>= 0``;
    divide by ``log2(nbins)`` for a [0, 1] diversity index.
    """
    v = np.asarray(values, dtype=float).ravel()
    v = v[np.isfinite(v)]
    nb = max(1, int(nbins))
    if v.size == 0:
        return 0.0
    lo = float(np.min(v)) if vmin is None else float(vmin)
    hi = float(np.max(v)) if vmax is None else float(vmax)
    if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
        return 0.0                                  # degenerate: one bin only
    counts, _edges = np.histogram(v, bins=nb, range=(lo, hi))
    total = float(counts.sum())
    if total <= 0.0:
        return 0.0                                  # all samples fell outside
    p = counts[counts > 0] / total
    h = float(-np.sum(p * np.log2(p)))
    return h if h > 0.0 else 0.0                     # clamp -0.0 / tiny negative


def entropy_signature(z, dx=1.0, nbins=64):
    """Compact, JSON-serialisable Shannon-entropy signature of a grid ``z``.

    Returns plain Python floats::

        {"slope_entropy":          float,   # bits, slope-magnitude histogram
         "elevation_entropy":      float,   # bits, normalized-elevation histogram
         "slope_entropy_norm":     float,   # slope_entropy / log2(nbins), in [0,1]
         "elevation_entropy_norm": float}   # elevation_entropy / log2(nbins)

    The slope distribution is :func:`_slope_degrees` (``np.gradient`` at spacing
    ``dx``) histogrammed with ``nbins`` bins over ``[0, max_slope]``; the
    elevation distribution is ``z`` normalized to [0, 1] over the finite cells
    and histogrammed with ``nbins`` bins over ``[0, 1]``. The ``*_norm`` values
    are the raw entropies divided by ``log2(nbins)`` and clamped to [0, 1]
    (``1.0`` = maximally diverse / uniform, ``0.0`` = all mass in one bin).

    NaN-safe: non-finite cells are ignored throughout. A constant field has
    zero slope everywhere -> ``slope_entropy == slope_entropy_norm == 0.0``; a
    field with no relief also has ``elevation_entropy == 0.0``. Deterministic.
    Carries the module's claim firewall: map-scale slope/elevation information
    content only -- not a traversability, hazard, geologic, or mission claim.
    """
    za = np.asarray(z, dtype=float)
    nb = max(1, int(nbins))
    denom = float(np.log2(nb)) if nb > 1 else 0.0

    def _norm(h):
        if denom <= 0.0:
            return 0.0
        return min(1.0, max(0.0, h / denom))

    # Slope distribution over [0, max_slope] (degrees), finite cells only.
    slope = _slope_degrees(za, dx)
    sfin = slope[np.isfinite(slope)]
    smax = float(np.max(sfin)) if sfin.size else 0.0
    slope_h = shannon_entropy(slope, nbins=nb, vmin=0.0, vmax=smax)

    # Elevation distribution over normalized z in [0, 1], finite cells only.
    zfin = za[np.isfinite(za)]
    elev_h = 0.0
    if zfin.size:
        zmin = float(np.min(zfin))
        zmax = float(np.max(zfin))
        rng = zmax - zmin
        if np.isfinite(rng) and rng > 0.0:
            zn = (za - zmin) / rng
            elev_h = shannon_entropy(zn, nbins=nb, vmin=0.0, vmax=1.0)

    return {
        "slope_entropy": float(slope_h),
        "elevation_entropy": float(elev_h),
        "slope_entropy_norm": float(_norm(slope_h)),
        "elevation_entropy_norm": float(_norm(elev_h)),
    }
