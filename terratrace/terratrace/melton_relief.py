"""Melton ruggedness & relief ratios -- classic basin-scale relief scalars.

Melton, M.A. (1965). The geomorphic and paleoclimatic significance of alluvial
deposits in southern Arizona. Journal of Geology 73(1), 1-38.
Pike, R.J. & Wilson, S.E. (1971). Elevation-relief ratio, hypsometric integral,
and geomorphic area-altitude analysis. GSA Bulletin 82(4), 1079-1084.

These are among the oldest and most portable single-number descriptors of how
much a surface rises relative to its horizontal size. Applied here to a single
DEM *tile* (not a delineated drainage basin) they summarise the tile's gross
relief and its average steepness with four scale-aware scalars::

    total relief        H   = p99(z) - p1(z)                 (metres)
    Melton ruggedness   R_m = H / sqrt(A)                    (dimensionless)
    relief ratio        R_h = H / L,   L = sqrt(A)           (dimensionless)
    elevation-relief    E   = (mean(z) - min(z)) / (max(z) - min(z))   in [0, 1]

where the tile "area" ``A = n_finite * dx^2`` is the footprint of the finite
cells (m^2) and ``L = sqrt(A)`` is its horizontal extent (m).

``H`` is a ROBUST relief: the 1st-to-99th-percentile spread of the finite
heights rather than a single-pixel max-min, so one MOLA spike or filled void
does not inflate it -- exactly the convention used by
:func:`terratrace.features.hypsometric_integral`. The Melton ruggedness number
``R_m = H / sqrt(A)`` (Melton 1965) normalises relief by the square root of area
and is the standard dimensionless measure of overall ruggedness; the
Schumm-style relief ratio ``R_h = H / L`` is the mean rise-over-run across the
tile's horizontal extent -- on a square tile it is the average along-axis
gradient. Note that because the tile has a single length scale ``L = sqrt(A)``,
``R_m`` and ``R_h`` COINCIDE here (both equal ``H / sqrt(A)``); they are
reported under both names because they are read differently -- ``R_m`` as a
dimensionless ruggedness number, ``R_h`` as a mean gradient -- and would differ
on a true basin where length and ``sqrt(area)`` are not the same. The
elevation-relief ratio ``E`` (Pike & Wilson 1971) is the fraction
of the relief band that lies below the mean height; it closely APPROXIMATES the
hypsometric integral and cross-checks :func:`features.hypsometric_integral` (the
two differ only by E's true min/max versus HI's robust p1/p99 band).

Degenerate inputs. A flat tile (``max == min``) or an all-nodata tile has zero
relief, so ``total_relief_m``, ``melton_ruggedness`` and ``relief_ratio`` are
all ``0.0`` (the ratios are ``0 / sqrt(A)``, taken as 0, and never divide by a
vanishing ``sqrt(A)``). The elevation-relief ratio is a genuine ``0 / 0`` there
and is returned as ``nan`` -- the same undefined-on-flat convention as
:func:`features.hypsometric_integral`, chosen so ``E`` tracks that sibling.

Units: ``dx`` is grid spacing in metres; ``H`` is in metres, ``A`` in m^2,
``L`` in m, and ``R_m``, ``R_h``, ``E`` are dimensionless. All outputs are plain
Python floats, JSON-serialisable and deterministic. Pure NumPy, NaN-safe
(nodata cells are dropped) -- no SciPy, no network, no disk.

Scientific boundary / claim firewall: these are classic GEOMETRIC relief and
ruggedness scalars (Melton 1965; Pike & Wilson 1971) applied at the tile scale
-- map-scale morphology only. They are NOT a basin-hydrology, hazard, or
mission claim; "area" is the tile footprint ``n_finite * dx^2``, not a
delineated drainage basin, and the ratios carry no process, erosion, climate,
or trafficability meaning on Mars, the Moon, Mercury, Ceres, Earth or any other
body.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "melton_signature",
]


def melton_signature(z, dx=1.0):
    """Melton (1965) ruggedness and relief ratios of a tile ``z``.

    Takes a 2-D elevation grid and grid spacing ``dx`` (metres) and returns a
    compact, JSON-serialisable dict of four tile-scale relief scalars::

        {"total_relief_m":          float,   # H = p99(z) - p1(z), metres
         "melton_ruggedness":       float,   # R_m = H / sqrt(A)
         "relief_ratio":            float,   # R_h = H / sqrt(A) (= H / L)
         "elevation_relief_ratio":  float}   # E = (mean-min)/(max-min), [0, 1]

    ``H`` is the robust 1st-99th-percentile relief of the finite heights; the
    tile area ``A = n_finite * dx^2`` and horizontal extent ``L = sqrt(A)``.
    Flat or all-nodata tiles yield relief and both ratios ``0.0`` with
    ``elevation_relief_ratio`` ``nan`` (an undefined ``0 / 0``, mirroring
    :func:`terratrace.features.hypsometric_integral`). Deterministic and
    NaN-safe (nodata cells are dropped, never raises). Carries the module's
    claim firewall: purely geometric tile-scale relief/ruggedness scalars, NOT
    a basin-hydrology, hazard, or mission claim on any body.
    """
    nan = float("nan")
    out = {
        "total_relief_m": 0.0,
        "melton_ruggedness": 0.0,
        "relief_ratio": 0.0,
        "elevation_relief_ratio": nan,
    }

    v = np.asarray(z, dtype=float)
    v = v[np.isfinite(v)]
    n = int(v.size)
    if n == 0:
        return out                       # all-nodata tile: zeros, E undefined

    dx = float(dx)
    if not np.isfinite(dx) or dx <= 0.0:
        dx = 1.0                         # degrade gracefully, never divide by 0

    # Robust total relief H = p99 - p1 (metres), as features.hypsometric_integral.
    lo = float(np.percentile(v, 1.0))
    hi = float(np.percentile(v, 99.0))
    H = hi - lo
    if H < 0.0:                          # guard float noise; percentiles sorted
        H = 0.0
    out["total_relief_m"] = H

    # Tile footprint A = n_finite * dx^2 (m^2) and horizontal extent L = sqrt(A).
    A = n * dx * dx
    L = float(np.sqrt(A))
    if L > 0.0:
        out["melton_ruggedness"] = float(H / L)
        out["relief_ratio"] = float(H / L)   # R_h = H / L; L = sqrt(A) on the tile

    # Elevation-relief ratio E = (mean - min) / (max - min); true extremes.
    zmin = float(np.min(v))
    zmax = float(np.max(v))
    rng = zmax - zmin
    if rng > 1e-12:
        out["elevation_relief_ratio"] = float((float(np.mean(v)) - zmin) / rng)
    # else: flat tile -> E stays nan (undefined 0/0, per the module convention)

    return out
