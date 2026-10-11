"""Openness-difference slope position (Yokoyama, Shirasawa & Pike, 2002).

The slope-position image ``D = Phi - Psi`` is the per-cell difference between
*positive* topographic openness ``Phi`` (the mean line-of-sight angle looking
UP toward the sky) and *negative* topographic openness ``Psi`` (the mean angle
looking DOWN toward the ground), both in degrees. It is one of the standard
DEM visualisations introduced by Yokoyama et al. (2002): positive openness is
large on exposed / convex sites and negative openness is large in pits /
concave sites, so differencing them isolates local *slope position*:

* ``D > 0`` on CONVEX ridge / crest / spur positions (``Phi`` exceeds ``Psi``);
* ``D < 0`` on CONCAVE valley / channel / pit positions (``Psi`` exceeds Phi);
* ``D ~ 0`` on planar midslopes, where the two openness fields coincide -- both
  are exactly 90 degrees on a flat surface and average to ~90 on a uniform
  tilt, so their difference vanishes.

This module adds no new horizon-scan machinery of its own. It REUSES the public
openness fields from :mod:`terratrace.openness` (imported lazily so importing
this module stays cheap) and simply differences them, then summarises the
result. The eight-azimuth definition, the NaN handling, and the 90-degree
flat-surface convention all live in that module and are inherited unchanged;
the ``radius`` (horizon length in cells) and ``dx`` arguments are passed
straight through, so the slope-position image is reported at whatever map
scale the caller selects.

Scientific boundary / claim firewall: this is a purely GEOMETRIC slope-position
measure derived from line-of-sight openness (Yokoyama 2002). It is a map-scale
*morphology / visualisation* descriptor only -- NOT a geological, surface-
process, traversability, hazard, or mission-readiness claim on Mars, the Moon,
Mercury, Ceres, Earth, or any other body. "Ridge", "valley" and "slope
position" are used in their abstract grid-geometry sense.

Reference:
    Yokoyama, R., Shirasawa, M., Pike, R.J. (2002). Visualizing topography by
    openness: a new application of image processing to DEMs. Photogrammetric
    Engineering & Remote Sensing 68(3), 257-265.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "openness_difference_field",
    "openness_difference_signature",
]


def openness_difference_field(z, dx=1.0, radius=10):
    """Slope-position image ``D = positive_openness - negative_openness``.

    Returns a ``float64`` array shaped like ``z`` holding, per cell, the
    difference (in degrees) between positive and negative topographic
    openness. ``D`` is strongly positive on convex ridge / crest positions,
    strongly negative in concave valleys / pits, and near zero on planar
    midslopes. ``dx`` (grid spacing in metres) and ``radius`` (horizon length
    in cells) are forwarded to :func:`terratrace.openness.openness`, which
    validates them and performs the NaN-safe horizon scan.

    NaN-safe: fully-masked cells fall back to openness 90 in both fields, so
    their difference is 0 and the output stays finite for any finite-or-NaN
    input, exactly as the openness engine guarantees.
    """
    from terratrace import openness  # lazy: keep import of this module cheap

    fields = openness.openness(z, dx=dx, radius=radius)
    positive = np.asarray(fields["positive"], dtype=np.float64)
    negative = np.asarray(fields["negative"], dtype=np.float64)
    return positive - negative


def openness_difference_signature(z, dx=1.0, flat_tol=5.0, radius=10):
    """Scalar slope-position signature of ``z`` as plain Python floats.

    Builds the slope-position image with :func:`openness_difference_field` and
    summarises its distribution::

        {"slopepos_mean", "slopepos_std",   # mean / std of D (degrees)
         "slopepos_p10", "slopepos_p90",    # 10th / 90th percentiles of D
         "ridge_fraction",                  # fraction of cells with D >  flat_tol
         "valley_fraction",                 # fraction of cells with D < -flat_tol
         "midslope_fraction"}               # fraction with |D| <= flat_tol

    The three fractions partition the finite cells and therefore sum to 1.0.
    ``flat_tol`` (degrees, default 5) is the half-width of the planar-midslope
    band around zero. All values are plain ``float`` so the signature is
    JSON-serialisable and deterministic. Statistics are taken over the finite
    cells only, so the entry point is NaN-safe; an all-nodata input yields NaN
    statistics with zero fractions. Carries the module's claim firewall: a
    purely geometric slope-position measure, not a process / mission claim.
    """
    nan = float("nan")
    out = {
        "slopepos_mean": nan,
        "slopepos_std": nan,
        "slopepos_p10": nan,
        "slopepos_p90": nan,
        "ridge_fraction": 0.0,
        "valley_fraction": 0.0,
        "midslope_fraction": 0.0,
    }

    d = openness_difference_field(z, dx=dx, radius=radius)
    vals = d[np.isfinite(d)]
    n = int(vals.size)
    if n == 0:
        return out

    tol = abs(float(flat_tol))
    out["slopepos_mean"] = float(np.mean(vals))
    out["slopepos_std"] = float(np.std(vals))
    out["slopepos_p10"] = float(np.percentile(vals, 10.0))
    out["slopepos_p90"] = float(np.percentile(vals, 90.0))
    out["ridge_fraction"] = float(np.count_nonzero(vals > tol) / n)
    out["valley_fraction"] = float(np.count_nonzero(vals < -tol) / n)
    out["midslope_fraction"] = float(np.count_nonzero(np.abs(vals) <= tol) / n)
    return out
