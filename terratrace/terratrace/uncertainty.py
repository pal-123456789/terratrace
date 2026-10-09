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


def _vector(ref_feats, cand_feats, rng, resample=True):
    """Base 4-dim distance vector (slope, relief, ruggedness, connectivity)."""
    v = []
    for f in DIST_FEATURES:
        r = ref_feats[f]; c = cand_feats[f]
        if resample:
            r = _resample(r, rng); c = _resample(c, rng)
        v.append(normalized_distance(c, r))
    scale = abs(ref_feats["connectivity_scalar"]) + 1e-6
    v.append(abs(cand_feats["connectivity_scalar"] - ref_feats["connectivity_scalar"]) / scale)
    return tuple(float(x) for x in v)


def bootstrap_pareto(ref_feats, cand_feats, n_boot=300, seed=0, extra_dims=None):
    """ref_feats: feature dict for the reference. cand_feats: {unit: feature dict}.

    extra_dims: optional {unit: tuple} of fixed extra decision dimensions (e.g. the
    extended aspect/hypsometric distances) appended to each resampled vector so the
    non-domination frequency reflects the SAME decision space as the main study.

    Returns per-unit non-domination frequency, clear-winner frequency, and per-unit
    distance confidence intervals (for the 4 base axes); plus overall decisiveness.
    """
    rng = np.random.default_rng(seed)
    extra_dims = extra_dims or {}
    units = list(cand_feats)
    nondom = {u: 0 for u in units}
    winner = {u: 0 for u in units}
    base_samples = {u: [] for u in units}
    for _ in range(n_boot):
        vecs = {}
        for u in units:
            base = _vector(ref_feats, cand_feats[u], rng, resample=True)
            base_samples[u].append(base)
            vecs[u] = base + tuple(float(x) for x in extra_dims.get(u, ()))
        nd = non_dominated(vecs)
        for u in nd:
            nondom[u] += 1
        if len(nd) == 1:
            winner[next(iter(nd))] += 1
    out = {"n_boot": n_boot, "seed": seed, "units": {}}
    names = list(DIST_FEATURES) + ["connectivity"]
    for u in units:
        arr = np.array(base_samples[u])  # (n_boot, 4)
        ci = {}
        for j, nm in enumerate(names):
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
