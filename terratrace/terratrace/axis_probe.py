"""The independent-axis probe: what the declared axes cannot see, and whether it matters.

WHY THIS MODULE EXISTS
----------------------
The lunar panel's three declared axes span one dimension (`terratrace.dependence`), so every
descriptor that is a function of roughness amplitude is the same descriptor wearing a different
name. The question this module answers is not "is there a fourth axis" -- it is the pair of
questions that actually decide whether the limitation matters:

  1. Is there a bank descriptor that carries information the three declared axes do not?
  2. Would adding it change the decision?

Question 2 is the one that gets skipped, and it is the one that can embarrass a conclusion. A Pareto
comparison over 8 units in 3 dimensions is expected to be fragile when a 4th coordinate arrives --
ANY 4th coordinate, including a random one. So this module ships its own null: the same frontier test
run against uniformly random coordinates. Without that control, "the frontier changed when we added
our axis" is not a result, it is a description of what adding a dimension does.

Two invariants are asserted rather than assumed, because both are cheap and both encode a way of
being wrong:

  * adding a coordinate to a Pareto comparison can only ever **promote** a co-winner, never remove
    one, so a removal is a machinery failure and not a finding (:func:`promoted_only`);
  * an `R2` computed with more parameters than a small sample can support is not evidence, so the
    estimate is **adjusted** and the raw chance level is computed alongside it
    (:func:`adjusted_r2`, :func:`chance_level_raw_r2`).

Measured values live in the artifact and the doc; this module is arithmetic and is tested on
synthetic input with no dataset present.
"""
from __future__ import annotations

import numpy as np

from . import decision, features

__all__ = [
    "chance_level_raw_r2", "adjusted_r2", "within_cell_cv",
    "engine_fractional_distance", "range_normalised_distance", "range_distance_vector",
    "layer1", "promoted_only", "classify", "plane", "declared_axes", "invariance_report",
    "NON_REDUNDANT", "PARTIALLY_INDEPENDENT", "REDUNDANT", "UNDEFINED",
]

NON_REDUNDANT = "NON_REDUNDANT"
PARTIALLY_INDEPENDENT = "PARTIALLY_INDEPENDENT"
REDUNDANT = "REDUNDANT"
UNDEFINED = "UNDEFINED"

# How far the mean must sit above the RMS for a coefficient of variation to mean anything.
#
# A CV is spread over mean, so a vector whose mean is a rounding error away from zero produces an
# enormous CV out of nothing: [1e-12, -1e-12, 2e-12, -2e-12, ...] has |mean|/rms = 0.10 and a CV
# near 10. The floor is 0.10 rather than something smaller because a signed descriptor centred on
# zero is exactly the case where "variation relative to the mean" is not a defined quantity -- and
# every legitimate candidate here (an elevation sigma, a roughness, a class fraction) sits far above
# it, since a non-negative quantity has |mean|/rms >= 1/sqrt(n) = 0.35.
MEAN_OVER_RMS_FLOOR = 0.10


# --------------------------------------------------------------------------- the estimate

def chance_level_raw_r2(n_units, n_predictors):
    """The R2 a random response would score, in expectation, on this many units and predictors.

    ``E[R2] = p / (n - 1)`` under the null with an intercept fitted. At n = 8 and p = 3 that is
    0.4286, which is why a raw-R2 threshold of "below 0.5" is a threshold slightly above noise and
    why this module reports adjusted R2 instead.
    """
    if n_units < 2 or n_predictors < 1 or n_predictors >= n_units - 1:
        return None
    return float(n_predictors) / float(n_units - 1)


def adjusted_r2(y, X):
    """Adjusted R2 of ``y`` on ``X`` (an intercept is fitted). ``(None, None)`` when undefined.

    Undefined is a distinct outcome from zero and is returned as such: a response with no spread has
    no R2, and a design with no residual degrees of freedom has no adjusted R2. Returning 0 for
    either would let a constant descriptor be ranked as a maximally INDEPENDENT one -- which is the
    exact mistake this function's adjusted form and its ``None`` convention both exist to prevent.
    """
    y = np.asarray(y, dtype=float)
    X = np.asarray(X, dtype=float)
    if X.ndim != 2 or y.ndim != 1 or X.shape[0] != y.shape[0]:
        raise ValueError(f"shape mismatch: y {y.shape}, X {X.shape}")
    n, p = X.shape
    if n <= p + 1:
        return None, None                      # no residual degrees of freedom
    if not (np.all(np.isfinite(y)) and np.all(np.isfinite(X))):
        return None, None                      # a non-finite value is not a low R2
    sst = float(((y - y.mean()) @ (y - y.mean())))
    if sst <= 0.0:
        return None, None
    design = np.column_stack([np.ones(n), X])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    r2 = 1.0 - float(resid @ resid) / sst
    adj = 1.0 - (1.0 - r2) * (n - 1) / (n - p - 1)
    return float(r2), float(adj)


def within_cell_cv(values):
    """Coefficient of variation across the compared units, or ``None`` when it is not meaningful.

    ``None`` covers the two ways this is undefined: no spread at all, and a mean so close to zero
    that the ratio is dominated by the denominator. The second guard matters for signed descriptors
    and for compositional fractions whose mean is near zero while their values are not.
    """
    v = np.asarray(values, dtype=float)
    if v.size < 2 or not np.all(np.isfinite(v)):
        return None
    rms = float(np.sqrt(np.mean(v ** 2)))
    if rms == 0.0:
        return None
    mean = abs(float(np.mean(v)))
    if mean < MEAN_OVER_RMS_FLOOR * rms:
        return None
    return float(np.std(v)) / mean


# --------------------------------------------------------------------------- the added axis

def engine_fractional_distance(reference_value, value):
    """The panel's own axial distance, or ``None`` where it is undefined.

    The panel path itself now REFUSES an undefined normalisation instead of emitting a NaN -- see
    :func:`decision.axial_fractional_distance`, which owns the policy -- but this wrapper keeps the
    ``None`` shape deliberately: the probe's job is to RECORD which descriptors cannot be
    normalised this way against their reference, not to run a decision on them. ``None`` is that
    record. Both-zero is not one of the undefined cases: it is an exact agreement, and it is 0.0.
    """
    try:
        return decision.axial_fractional_distance(reference_value, value)
    except decision.UndefinedNormalisation:
        return None


def range_distance_vector(values, ref_index):
    """Per-unit distance from the reference normalised by the within-cell RANGE.

    The probe's normalisation for an added axis. Unlike :func:`engine_fractional_distance` it is
    defined whenever the units differ at all, and it is the same shape of quantity -- a distance
    from the reference, so the Pareto input keeps its meaning: nearest wins.
    """
    v = np.asarray(values, dtype=float)
    if not np.all(np.isfinite(v)):
        return None
    span = float(v.max() - v.min())
    if span <= 0.0:
        return None
    return np.abs(v - v[ref_index]) / span


def layer1(distances):
    """The non-dominated set for a ``{unit: [axis values]}`` mapping, sorted. Pareto, no composite."""
    return sorted(decision.non_dominated(distances))


def promoted_only(base, extended):
    """``(promoted, removed)`` between two layer-1 sets, with the invariant enforced by the caller.

    Adding a coordinate can only promote: dominance becomes harder, never easier. A non-empty
    ``removed`` therefore means something upstream is wrong -- a NaN in the added coordinate is the
    usual cause, since ``NaN <= x`` is False and quietly changes what dominates what -- and it must
    be raised rather than reported as a finding.
    """
    base, extended = set(base), set(extended)
    return sorted(extended - base), sorted(base - extended)


def classify(median_adjusted_r2, non_redundant_at=0.0, partially_independent_at=0.25):
    """Bucket a median adjusted R2. ``None`` is UNDEFINED, never REDUNDANT by default."""
    if median_adjusted_r2 is None:
        return UNDEFINED
    if median_adjusted_r2 <= non_redundant_at:
        return NON_REDUNDANT
    if median_adjusted_r2 <= partially_independent_at:
        return PARTIALLY_INDEPENDENT
    return REDUNDANT


# --------------------------------------------------------------------------- the analytic half

def plane(gradient, theta_deg, n=18, dx=500.0):
    """A tilted plane with gradient magnitude ``gradient`` at azimuth ``theta_deg`` (metres, degrees).

    The family that makes the blindness question answerable: one free parameter, and if the three
    declared axes are invariant under a transformation of it, they cannot see that dimension.
    """
    j, i = np.meshgrid(np.arange(n), np.arange(n), indexing="xy")
    th = np.radians(float(theta_deg))
    return float(gradient) * (i * dx * np.cos(th) + j * dx * np.sin(th))


def declared_axes(z, dx):
    """The three declared axes, computed exactly as the panel computes them.

    Duplicated here rather than imported because the panel's ``axes_of`` lives in a script, not in
    the package; a test asserts the two agree to 1e-12 so the duplication cannot drift into being a
    different measurement.
    """
    z = np.asarray(z, dtype=float)
    slope = features.slope_deg(z, dx, dx)
    relief = features.relief(z, window=3, alpha=0.0)
    finite = np.isfinite(z)
    return {"mean_slope_deg": float(np.nanmean(slope)),
            "mean_relief3_m": float(np.nanmean(relief)),
            "elev_std_m": float(np.nanstd(z[finite]))}


def _ops():
    return {"theta_plus_90": lambda t: t + 90.0,
            "ninety_minus_theta": lambda t: 90.0 - t,
            "theta_plus_180": lambda t: t + 180.0,
            "theta_plus_45": lambda t: t + 45.0}


def invariance_report(gradient=0.30, n=18, dx=500.0, thetas=(0.0, 7.0, 19.0, 33.0, 64.0, 88.0, 102.0, 137.0)):
    """Max absolute change in each declared axis under each azimuth operation, on planes.

    Returns ``{operation: {axis: max_abs_change}}``. The operation is applied at the same azimuth it
    is compared from -- mapping a SET of azimuths and taking a maximum across the set answers a
    different question, and answers it wrongly: it measures the spread of the family rather than the
    invariance of the operation. The first version of this function did that and reported the three
    axes as blind to nothing.
    """
    keys = ("mean_slope_deg", "mean_relief3_m", "elev_std_m")
    out = {}
    for name, fn in _ops().items():
        worst = {k: 0.0 for k in keys}
        for t in thetas:
            a = declared_axes(plane(gradient, t, n=n, dx=dx), dx)
            b = declared_axes(plane(gradient, fn(t), n=n, dx=dx), dx)
            for k in keys:
                worst[k] = max(worst[k], abs(a[k] - b[k]))
        out[name] = worst
    return out
