"""Resampling-based significance for terrain-morphology distances.

These are DISTRIBUTION-LEVEL morphology statistics only -- a claim firewall.
Every function here operates on the *shape* of elevation-sample distributions
via :mod:`terratrace.distances`; none makes a physical, geological, or mission
claim about any surface.

A single point distance cannot say whether candidate A is *meaningfully*
closer to a reference than candidate B. The permutation test below answers one
narrow question -- "could this closeness-gap arise by chance under random
relabelling of the pooled samples?" -- and nothing about why two terrains
differ or what that would imply for any mission.

All functions ignore NaN, operate on 1-D samples, and are deterministic given
a seed (one ``np.random.default_rng(seed)`` per call).
"""
from __future__ import annotations

import numpy as np

from terratrace import distances


def _finite(x):
    x = np.asarray(x, dtype=float).ravel()
    return x[np.isfinite(x)]


def bootstrap_distance_ci(ref, x, n_boot=1000, seed=0, scale=None, alpha=0.05):
    """Bootstrap confidence interval for the normalized distance of ``x`` to ``ref``.

    Resamples ``x`` and ``ref`` independently with replacement (over their
    finite values) ``n_boot`` times, recomputing
    :func:`distances.normalized_distance` each iteration, and returns the
    median plus the ``alpha/2`` and ``1 - alpha/2`` percentile bounds.

    Returns ``{"median", "lo", "hi", "n_boot"}``. NaN-safe: if either sample
    has no finite values every statistic is NaN.
    """
    xf = _finite(x)
    rf = _finite(ref)
    n_boot = int(n_boot)
    if xf.size == 0 or rf.size == 0:
        return {"median": float("nan"), "lo": float("nan"),
                "hi": float("nan"), "n_boot": n_boot}
    rng = np.random.default_rng(seed)
    dists = np.empty(n_boot, dtype=float)
    for i in range(n_boot):
        xi = xf[rng.integers(0, xf.size, xf.size)]
        ri = rf[rng.integers(0, rf.size, rf.size)]
        dists[i] = distances.normalized_distance(xi, ri, scale)
    lo = float(np.nanpercentile(dists, 100.0 * (alpha / 2.0)))
    hi = float(np.nanpercentile(dists, 100.0 * (1.0 - alpha / 2.0)))
    med = float(np.nanmedian(dists))
    return {"median": med, "lo": lo, "hi": hi, "n_boot": n_boot}


def permutation_closer_test(ref, a, b, n_perm=2000, seed=0, scale=None):
    """One-sided permutation test that A is closer to ``ref`` than B.

    ``observed = d(a, ref) - d(b, ref)`` (negative => A closer). The finite
    values of ``a`` and ``b`` are pooled; each of ``n_perm`` permutations
    randomly repartitions the pool into two groups of the ORIGINAL sizes of
    ``a`` and ``b`` and recomputes ``diff = d(groupA, ref) - d(groupB, ref)``::

        p_value_one_sided = (1 + #{diff <= observed}) / (n_perm + 1)
        p_value_two_sided = (1 + #{|diff| >= |observed|}) / (n_perm + 1)

    The one-sided p-value is the chance of seeing A at least this much closer
    under random relabelling. One ``np.random.default_rng(seed)`` drives all
    permutations. NaN-safe; if either sample is empty the distances are NaN
    and both p-values are 1.0.
    """
    af = _finite(a)
    bf = _finite(b)
    n_perm = int(n_perm)
    a_dist = distances.normalized_distance(af, ref, scale)
    b_dist = distances.normalized_distance(bf, ref, scale)
    if (af.size == 0 or bf.size == 0
            or not np.isfinite(a_dist) or not np.isfinite(b_dist)):
        return {
            "observed_diff": float("nan"),
            "p_value_one_sided": 1.0,
            "p_value_two_sided": 1.0,
            "a_distance": float("nan"),
            "b_distance": float("nan"),
            "a_closer": False,
            "significant": False,
            "n_perm": n_perm,
        }
    observed = a_dist - b_dist
    abs_obs = abs(observed)
    pool = np.concatenate([af, bf])
    na = af.size
    rng = np.random.default_rng(seed)
    cnt_one = 0
    cnt_two = 0
    for _ in range(n_perm):
        perm = rng.permutation(pool)
        diff = (distances.normalized_distance(perm[:na], ref, scale)
                - distances.normalized_distance(perm[na:], ref, scale))
        if diff <= observed:
            cnt_one += 1
        if abs(diff) >= abs_obs:
            cnt_two += 1
    p_one = (1 + cnt_one) / (n_perm + 1)
    p_two = (1 + cnt_two) / (n_perm + 1)
    return {
        "observed_diff": float(observed),
        "p_value_one_sided": float(p_one),
        "p_value_two_sided": float(p_two),
        "a_distance": float(a_dist),
        "b_distance": float(b_dist),
        "a_closer": bool(observed < 0),
        "significant": bool(p_one < 0.05),
        "n_perm": n_perm,
    }


def effect_size(ref, a, b, scale=None):
    """Standardized closeness gap in ``[-1, 1]``; positive => A closer to ref.

    ::

        (d(b, ref) - d(a, ref)) / (d(a, ref) + d(b, ref) + 1e-9)

    ``+1`` means A sits essentially on top of ``ref`` while B is far away;
    ``0`` means both candidates are equally close; ``-1`` means B is the close
    one. This is a pure distribution-shape summary, not a physical effect.
    Returns NaN if a distance is undefined (empty sample).
    """
    d_a = distances.normalized_distance(a, ref, scale)
    d_b = distances.normalized_distance(b, ref, scale)
    return float((d_b - d_a) / (d_a + d_b + 1e-9))
