"""Kreslavsky & Head (2000) differential-slope baseline roughness -- a gridded
adaptation of the canonical Mars/MOLA kilometre-scale roughness metric.

Kreslavsky, M. A., & Head, J. W. (2000). Kilometer-scale roughness of Mars:
Results from MOLA data analysis. Journal of Geophysical Research: Planets,
105(E11), 26695-26711.

The original metric is defined on 1-D MOLA altimetry PROFILES. At a baseline
``L`` it takes three points spaced ``L/2`` apart and forms the *differential
slope*: the right half-segment slope minus the left half-segment slope -- a
second difference of elevation along the track, expressed as an angle. The
roughness of a region at baseline ``L`` is the MEDIAN of the absolute
differential slope over all triples. Being a slope *difference* it removes any
regional tilt and isolates how much the surface bends at scale ``L``; the median
is robust to the heavy tails of planetary topography. This is the quantity shown
in NASA's global MOLA roughness maps.

This module is an explicit, documented GRIDDED ADAPTATION of that 1-D profile
metric: it treats every grid ROW and every grid COLUMN as a profile and pools
them. For a baseline ``b`` metres on a grid of spacing ``dx`` metres the
half-baseline in cells is ``k = max(1, round(b / (2*dx)))``, and for every
interior cell the along-x differential slope is

    d2x          = z[i, j+k] - 2*z[i, j] + z[i, j-k]      # second difference
    diff_slope_x = degrees( arctan( d2x / (k*dx) ) )      # a slope DIFFERENCE, deg

(``d2x / (k*dx)`` is exactly the right half-slope minus the left half-slope),
with the along-y value formed analogously from ``z[i+k, j]``, ``z[i, j]`` and
``z[i-k, j]``. Cells within ``k`` of a border have no complete triple and are
excluded (``nan``); any triple containing a ``nan`` is excluded likewise. The
baseline roughness is the median of the pooled absolute along-x and along-y
differential slopes, in degrees.

Two analytic properties anchor the code and its validation oracle: a tilted
PLANE (linear field) has an identically zero second difference, so its baseline
roughness is exactly ``0`` at every baseline; and the paraboloid
``z = q*(x^2 + y^2)`` has a CONSTANT differential slope
``degrees(arctan(2*q*k*dx))`` at half-baseline ``k`` (the second difference of a
quadratic is constant), reproducing a known closed form.

Units: ``dx`` and baselines are metres; every roughness value is an angle in
DEGREES. Pure NumPy, NaN-safe, deterministic -- no SciPy, no network.

Scientific boundary / claim firewall: this is a map-scale *morphology /
roughness* descriptor of the sampled elevation grid only. It is NOT a
traversability, trafficability, hazard, slope-stability, geologic-origin, or
mission-readiness claim, and nothing here estimates rover behaviour or
rock-scale obstacles.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "half_baseline_cells",
    "differential_slope",
    "baseline_roughness",
    "roughness_profile",
    "kh_roughness_signature",
]


def half_baseline_cells(dx, baseline_m):
    """Half-baseline expressed in whole grid cells.

    ``k = max(1, round(baseline_m / (2*dx)))`` -- the integer cell offset used by
    the three-point second difference (the samples sit ``L/2`` apart, i.e. ``k``
    cells on each side of the centre). Clamped to at least ``1`` so the stencil
    is never degenerate. ``dx`` must be a positive, finite grid spacing in
    metres. Exposed so callers (and tests) can derive ``k`` exactly as the
    module does.
    """
    dx = float(dx)
    if not np.isfinite(dx) or dx <= 0.0:
        raise ValueError("dx must be a positive, finite grid spacing in metres")
    return max(1, int(round(float(baseline_m) / (2.0 * dx))))


def differential_slope(z, dx, baseline_m):
    """Along-x and along-y differential slope of ``z`` at a baseline, in DEGREES.

    Treats grid rows and columns as 1-D profiles (Kreslavsky & Head 2000, gridded
    adaptation). With ``k = half_baseline_cells(dx, baseline_m)`` the along-x
    second difference at an interior cell is
    ``d2x = z[i, j+k] - 2*z[i, j] + z[i, j-k]`` and the differential slope is
    ``degrees(arctan(d2x / (k*dx)))`` -- the right half-segment slope minus the
    left, as an angle. The along-y value is formed analogously from
    ``z[i+k, j]``, ``z[i, j]`` and ``z[i-k, j]``.

    Parameters
    ----------
    z : 2-D array of elevations in metres (NaN = nodata).
    dx : square grid spacing in metres (> 0).
    baseline_m : the roughness baseline ``b`` in metres.

    Returns
    -------
    (diff_slope_x, diff_slope_y) : two float64 arrays shaped like ``z``, in
        DEGREES. Along-x values are valid for every row but only for interior
        columns ``k <= j < cols-k`` (the row ends have no complete x-triple);
        along-y mirrors this over rows. Border cells, and any cell whose triple
        contains a ``nan``, are ``nan`` -- so the finite entries are exactly the
        complete, finite triples.
    """
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    k = half_baseline_cells(dx, baseline_m)
    rows, cols = z.shape
    denom = k * float(dx)
    dsx = np.full(z.shape, np.nan, dtype=float)
    dsy = np.full(z.shape, np.nan, dtype=float)
    if cols > 2 * k:
        d2x = z[:, 2 * k:] - 2.0 * z[:, k:cols - k] + z[:, :cols - 2 * k]
        dsx[:, k:cols - k] = np.degrees(np.arctan(d2x / denom))
    if rows > 2 * k:
        d2y = z[2 * k:, :] - 2.0 * z[k:rows - k, :] + z[:rows - 2 * k, :]
        dsy[k:rows - k, :] = np.degrees(np.arctan(d2y / denom))
    return dsx, dsy


def baseline_roughness(z, dx, baseline_m):
    """Median absolute differential slope (degrees) pooled over x and y.

    The Kreslavsky & Head (2000) baseline roughness, gridded: form the along-x
    and along-y differential slopes at ``baseline_m`` (see
    :func:`differential_slope`), pool the ABSOLUTE values of every valid cell
    from both directions, and return their MEDIAN in degrees. Returns ``nan`` if
    no valid (complete, finite) triple exists at this baseline -- e.g. the
    baseline is too large for the grid, or the grid is all-NaN. NaN-safe and
    deterministic.
    """
    dsx, dsy = differential_slope(z, dx, baseline_m)
    pooled = np.concatenate((np.abs(dsx).ravel(), np.abs(dsy).ravel()))
    pooled = pooled[np.isfinite(pooled)]
    if pooled.size == 0:
        return float("nan")
    return float(np.median(pooled))


def roughness_profile(z, dx, baselines_m):
    """Baseline roughness at each requested baseline, as an ascending dict.

    Returns ``{float(baseline_m): roughness_deg}`` with one entry per baseline in
    ``baselines_m``, inserted in ASCENDING baseline order (keys are plain Python
    floats in metres; values are the degrees roughness from
    :func:`baseline_roughness`, possibly ``nan`` for a baseline too large to fit
    the grid). This traces the gridded analogue of the Kreslavsky & Head
    multi-baseline roughness-vs-scale curve.
    """
    z = np.asarray(z, dtype=float)
    out = {}
    for b in sorted(float(x) for x in baselines_m):
        out[float(b)] = float(baseline_roughness(z, dx, b))
    return out


def _default_baselines(z, dx):
    """Default baselines ``[2*dx, 4*dx, 8*dx]`` clamped so each half-baseline
    ``k`` leaves at least one valid interior line on the grid
    (``min(rows, cols) > 2*k``). Returns a list of float metres -- fewer than
    three only on a small grid."""
    rows, cols = np.asarray(z).shape
    min_dim = min(int(rows), int(cols))
    out = []
    for mult in (2.0, 4.0, 8.0):
        b = mult * float(dx)
        if min_dim > 2 * half_baseline_cells(dx, b):
            out.append(b)
    return out


def _loglog_slope(profile):
    """Least-squares slope of ``log(roughness)`` vs ``log(baseline)`` over the
    profile's finite, strictly-positive points; ``nan`` if fewer than three such
    points. The slope is independent of the log base."""
    bs = np.array(sorted(profile), dtype=float)
    rs = np.array([profile[b] for b in bs], dtype=float)
    good = np.isfinite(bs) & (bs > 0.0) & np.isfinite(rs) & (rs > 0.0)
    bs, rs = bs[good], rs[good]
    if bs.size < 3:
        return float("nan")
    return float(np.polyfit(np.log(bs), np.log(rs), 1)[0])


def kh_roughness_signature(z, dx, baselines_m=None):
    """Compact, JSON-serialisable differential-slope roughness signature.

    Builds the :func:`roughness_profile` over ``baselines_m`` (default
    ``[2*dx, 4*dx, 8*dx]`` clamped so each half-baseline fits the grid) and
    returns plain Python floats::

        {"baseline_roughness_fine":   float,   # roughness at the SMALLEST baseline
         "baseline_roughness_coarse": float,   # roughness at the LARGEST baseline
         "profile": {float(baseline_m): roughness_deg, ...},   # ascending
         "profile_loglog_slope": float}        # LS slope of log(rough) vs log(baseline),
                                               # or nan if fewer than 3 usable points

    Every value is a degrees roughness (angle) except the dimensionless log-log
    slope; the ``profile`` keys are float baselines in metres. ``nan`` appears
    where a descriptor is undefined (an empty / too-coarse profile, or too few
    points for the slope). Carries the module's claim firewall: map-scale
    morphology / roughness only -- not a traversability, hazard, geologic, or
    mission claim.
    """
    z = np.asarray(z, dtype=float)
    if baselines_m is None:
        baselines_m = _default_baselines(z, dx)
    profile = roughness_profile(z, dx, baselines_m)
    if profile:
        keys = sorted(profile)
        fine = float(profile[keys[0]])
        coarse = float(profile[keys[-1]])
    else:
        fine = coarse = float("nan")
    return {
        "baseline_roughness_fine": fine,
        "baseline_roughness_coarse": coarse,
        "profile": {float(b): float(r) for b, r in profile.items()},
        "profile_loglog_slope": _loglog_slope(profile),
    }

