"""Beven & Kirkby (1979) Topographic Wetness Index -- an area/slope composite.

Beven, K. J., & Kirkby, M. J. (1979). A physically based, variable contributing
area model of basin hydrology. Hydrological Sciences Bulletin, 24(1), 43-69.
[the TWI = ln(a / tan beta) steady-state wetness-propensity index]

The topographic wetness index combines how much area drains THROUGH a cell with
how STEEP that cell is:

    TWI = ln( a / tan(beta) )

where ``a`` is the specific catchment area -- the upslope contributing area per
unit contour width -- and ``beta`` is the local slope angle. TWI is HIGH where a
large contributing area routes through a gentle cell (area piles up on gentle
ground) and LOW on steep, divergent cells that shed what little drains to them.
It is the classic steady-state index of Beven & Kirkby (1979).

Estimation (pure geometry, reusing the engine's operators). Per finite cell:

    a    = flow_accumulation(z) * dx           # specific catchment area, metres
                                               #   (per-cell area acc*dx^2 over a
                                               #   contour width ~ dx leaves acc*dx)
    tanb = max( tan(radians(slope_deg)), eps)  # local slope tangent, floored at
                                               #   eps = 1e-3 so flat cells do not
                                               #   blow the ratio up
    TWI  = ln( a / tanb )                       # natural log

reusing the depression-filled D8 :func:`terratrace.drainage.flow_accumulation`
for the contributing area and :func:`terratrace.features.slope_deg` for the slope
angle, both imported lazily so importing this module stays cheap. ``a >= dx`` on
every finite cell (D8 accumulation is ``>= 1``) and ``tanb >= eps``, so the ratio
is strictly positive and the natural log is always defined.

Units: ``dx`` is the grid spacing in metres; ``a`` is in metres and ``beta`` is a
true angle, so TWI is a dimensionless log index. Pure NumPy, NaN-safe (nodata
cells and the gradient neighbours they contaminate carry NaN and are dropped from
the signature), deterministic -- no SciPy, no network, no disk.

Scientific boundary / claim firewall: TWI here is a purely GEOMETRIC area/slope
composite -- a steady-state wetness-PROPENSITY index of the sampled height field.
It is NOT a claim of soil moisture, actual water, saturation, hydrology, climate,
erosion, or mission behaviour on Mars, the Moon, Mercury, Ceres, Earth or any
other body. "Contributing area" is the geometric D8 flow accumulation on a
depression-filled grid, exactly as the flow-accumulation operator is defined in
geomorphometry, and carries no hydrological meaning here; "wetness" names the
index's abstract area-over-slope form, not any physical wetness.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "twi_field",
    "twi_signature",
]


def twi_field(z, dx=1.0):
    """Topographic Wetness Index field ``ln(a / tan beta)`` (Beven & Kirkby 1979).

    Returns a float64 array shaped like ``z``. For every finite cell::

        a    = flow_accumulation(z) * dx            # specific catchment area (m)
        tanb = max(tan(radians(slope_deg(z))), 1e-3)
        twi  = log(a / tanb)                        # natural log

    The depression-filled D8 accumulation and the slope angle are imported lazily
    from :mod:`terratrace.drainage` and :mod:`terratrace.features` so importing
    this module stays cheap. ``tanb`` is floored at ``eps = 1e-3`` so (near-)flat
    cells do not blow the ratio up. NaN cells (nodata and the gradient neighbours
    they contaminate) propagate NaN; the function never raises on NaN input.

    A purely geometric area/slope composite -- see the module claim firewall; NOT
    a soil-moisture, water, hydrology, or mission claim on any body.
    """
    from terratrace import drainage, features

    z = np.asarray(z, dtype=float)
    dx = float(dx)
    acc = drainage.flow_accumulation(z)             # >= 1 on finite cells, NaN else
    a = acc * dx                                    # specific catchment area (m)
    beta_rad = np.radians(features.slope_deg(z, dx, dx))
    # np.maximum (not np.fmax) PROPAGATES NaN, so nodata cells stay NaN here.
    tanb = np.maximum(np.tan(beta_rad), 1e-3)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.log(a / tanb)


def twi_signature(z, dx=1.0):
    """Compact, JSON-serialisable summary of the TWI field over FINITE cells.

    Builds :func:`twi_field` and reduces its finite cells to five plain floats::

        {"twi_mean":   float,   # mean   TWI over finite cells
         "twi_median": float,   # median TWI
         "twi_p10":    float,   # 10th percentile (dry/divergent tail)
         "twi_p90":    float,   # 90th percentile (wet/convergent tail)
         "twi_std":    float}   # spread of TWI

    All five are ``float('nan')`` if the field has no finite cell. Deterministic
    and NaN-safe (non-finite cells are dropped before the reduction). Carries the
    module claim firewall: a purely geometric area/slope composite, NOT a
    soil-moisture / water / hydrology claim on any body.
    """
    field = twi_field(z, dx=dx)
    vals = field[np.isfinite(field)]
    nan = float("nan")
    if vals.size == 0:
        return {"twi_mean": nan, "twi_median": nan, "twi_p10": nan,
                "twi_p90": nan, "twi_std": nan}
    return {
        "twi_mean": float(np.mean(vals)),
        "twi_median": float(np.median(vals)),
        "twi_p10": float(np.percentile(vals, 10.0)),
        "twi_p90": float(np.percentile(vals, 90.0)),
        "twi_std": float(np.std(vals)),
    }
