"""Bootstrap uncertainty for morphology distances and the Pareto decision.

Point distances hide sampling error. This module resamples the terrain-feature
distributions with replacement to put confidence intervals on each distance and
to turn the Pareto decision into a *frequency*: how often each candidate is
non-dominated, and how often a single unit is the clear winner. That converts
"B beats A" into "B is non-dominated in 78% of resamples", which is the honest,
scientist-grade statement.
"""
from __future__ import annotations

import numpy as np

from .distances import normalized_distance
from .decision import non_dominated

DIST_FEATURES = ("slope", "relief", "ruggedness")


def _resample(arr, rng):
    a = np.asarray(arr, dtype=float)
    a = a[np.isfinite(a)]
    if a.size == 0:
        return a
    idx = rng.integers(0, a.size, a.size)
    return a[idx]


def bootstrap_pareto(ref_feats, cand_feats, n_boot=300, seed=0, extra_dims=None, scales=None):
    """ref_feats: feature dict for the reference. cand_feats: {unit: feature dict}.

    Paired bootstrap: on each iteration the reference distributions are resampled
    ONCE and reused for every candidate (so candidates are compared against the
    same reference draw), and each candidate is resampled once. `scales` gives the
    fixed per-feature normalizers (reference IQR) so axes are comparable across
    candidates. `extra_dims` appends fixed extended dimensions so non-domination
    is computed in the same space as the main decision.

    NOTE: resampling treats pixels as independent. DEM pixels are spatially
    autocorrelated, so these CIs are OPTIMISTIC (too narrow); treat them as a
    lower bound on uncertainty. A spatial/block bootstrap is on the roadmap.
    """
    rng = np.random.default_rng(seed)
    extra_dims = extra_dims or {}
    units = list(cand_feats)
    nondom = {u: 0 for u in units}
    winner = {u: 0 for u in units}
    base_samples = {u: [] for u in units}
    for _ in range(n_boot):
        ref_rs = {f: _resample(ref_feats[f], rng) for f in DIST_FEATURES}
        vecs = {}
        for u in units:
            cf = cand_feats[u]
            base = []
            for f in DIST_FEATURES:
                s = None if scales is None else scales.get(f)
                base.append(normalized_distance(_resample(cf[f], rng), ref_rs[f], scale=s))
            cscale = abs(ref_feats["connectivity_scalar"]) + 1e-6
            conn = abs(cf["connectivity_scalar"] - ref_feats["connectivity_scalar"]) / cscale
            base = tuple(float(x) for x in base)
            base_samples[u].append(base)
            vecs[u] = base + (float(conn),) + tuple(float(x) for x in extra_dims.get(u, ()))
        nd = non_dominated(vecs)
        for u in nd:
            nondom[u] += 1
        if len(nd) == 1:
            winner[next(iter(nd))] += 1
    out = {"n_boot": n_boot, "seed": seed,
           "note": "CIs assume independent pixels; spatial autocorrelation makes them optimistic.",
           "units": {}}
    for u in units:
        arr = np.array(base_samples[u])  # (n_boot, 3) for the distributional axes
        ci = {}
        for j, nm in enumerate(DIST_FEATURES):
            col = arr[:, j]
            ci[nm] = [float(np.percentile(col, 2.5)), float(np.percentile(col, 50)),
                      float(np.percentile(col, 97.5))]
        out["units"][u] = {
            "nondominated_freq": nondom[u] / n_boot,
            "clear_winner_freq": winner[u] / n_boot,
            "distance_ci": ci,
        }
    out["decisive_freq"] = sum(winner.values()) / n_boot
    return out
