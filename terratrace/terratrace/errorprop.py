"""Analytic propagation of DEM vertical accuracy into morphology-feature uncertainty.

Translate a DEM's stated 1-sigma vertical accuracy ``sigma_z`` (metres) into
1-sigma uncertainty on the map-scale morphology features (slope angle, local
relief, detrended ruggedness) by first-order (linearised) error propagation.

Model (central-difference gradient, INDEPENDENT per-pixel vertical error)::

    gx = (zE - zW) / (2 dx),   gy = (zN - zS) / (2 dx)
      => var(gx) = var(gy) = sigma_z^2 / (2 dx^2)
      => sigma_g = sigma_z / (dx * sqrt(2))
    G = sqrt(gx^2 + gy^2) = tan(slope),   sigma_G ~= sigma_g
    theta = atan(G),   dtheta/dG = 1 / (1 + G^2)
      => sigma_theta = sigma_G / (1 + G^2)   [radians]

HONEST CAVEAT: this assumes INDEPENDENT per-pixel vertical errors. Exactly like
the independent-pixel bootstrap, that assumption makes every number here an
OPTIMISTIC LOWER BOUND on the true uncertainty -- real DEM errors are spatially
correlated (striping, swath/tile seams, co-registration, terrain-dependent
bias), which inflates feature uncertainty above these estimates. The relief and
ruggedness bounds are additionally rough (window residuals partially cancel the
per-pixel noise). These are MAP-SCALE MORPHOLOGY uncertainties only; they make
no mechanical, trafficability, or mission claim.
"""
from __future__ import annotations

import math


def slope_sigma_deg(sigma_z, dx, slope_deg=0.0):
    """1-sigma uncertainty (degrees) on slope ANGLE given vertical accuracy sigma_z.

    With a central-difference gradient and independent per-pixel error the
    gradient-magnitude error is ``sigma_G = sigma_z / (dx * sqrt(2))`` on
    ``G = tan(slope)``; propagating through ``theta = atan(G)``
    (``dtheta/dG = 1/(1+G^2)``) gives ``degrees(sigma_G / (1 + G^2))``. Largest
    on flat ground, smaller as the terrain steepens (the ``1/(1+G^2)`` factor)
    and as ``dx`` grows. Optimistic lower bound (see module docstring).
    """
    if dx <= 0:
        raise ValueError("dx must be positive metres")
    if sigma_z < 0:
        raise ValueError("sigma_z must be >= 0 metres")
    G = math.tan(math.radians(slope_deg))
    sigma_G = sigma_z / (dx * math.sqrt(2.0))
    return math.degrees(sigma_G / (1.0 + G * G))


def relief_sigma_m(sigma_z):
    """1-sigma uncertainty (m) on local relief, which is a difference of two pixels.

    Relief is ``hi - lo``; a difference of two independent pixels propagates
    EXACTLY as ``sqrt(2) * sigma_z``. Optimistic: in a real DEM the two extremal
    pixels carry correlated error (see module docstring).
    """
    if sigma_z < 0:
        raise ValueError("sigma_z must be >= 0 metres")
    return math.sqrt(2.0) * float(sigma_z)


def ruggedness_sigma_m(sigma_z):
    """Rough 1-sigma bound (m) on detrended ruggedness (RMS plane residual).

    The RMS residual after removing a local best-fit plane is of the ORDER of
    the per-pixel vertical noise, so this returns ``~ sigma_z`` as a rough bound.
    It is deliberately approximate -- the exact factor depends on window size and
    the plane-fit degrees of freedom -- and, like the rest of the module,
    optimistic.
    """
    if sigma_z < 0:
        raise ValueError("sigma_z must be >= 0 metres")
    return float(sigma_z)


def propagate_feature_uncertainty(sigma_z, dx, median_slope_deg=0.0):
    """Propagate a DEM vertical accuracy into feature 1-sigma uncertainties.

    Returns a dict carrying the inputs (``sigma_z``, ``dx``) alongside the
    propagated ``slope_sigma_deg`` (evaluated at ``median_slope_deg``),
    ``relief_sigma_m`` and ``ruggedness_sigma_m``. All are optimistic lower
    bounds under the independent-pixel assumption (see module docstring).
    """
    if dx <= 0:
        raise ValueError("dx must be positive metres")
    if sigma_z < 0:
        raise ValueError("sigma_z must be >= 0 metres")
    return {
        "sigma_z": float(sigma_z),
        "dx": float(dx),
        "slope_sigma_deg": slope_sigma_deg(sigma_z, dx, median_slope_deg),
        "relief_sigma_m": relief_sigma_m(sigma_z),
        "ruggedness_sigma_m": ruggedness_sigma_m(sigma_z),
    }


def for_source(source_id, dx, median_slope_deg=0.0):
    """Propagate a CATALOG source's published vertical accuracy into feature sigmas.

    Looks up ``catalog.vertical_accuracy_for(source_id)`` (an approximate 1-sigma
    vertical RMSE in metres) and returns
    :func:`propagate_feature_uncertainty` with the ``source_id`` and its
    ``vertical_accuracy_m`` added. Optimistic lower bounds (see module docstring).
    """
    from terratrace import catalog  # lazy: keeps this pure-math module import-light
    sigma_z = catalog.vertical_accuracy_for(source_id)
    out = propagate_feature_uncertainty(sigma_z, dx, median_slope_deg)
    out["source_id"] = source_id
    out["vertical_accuracy_m"] = float(sigma_z)
    return out
