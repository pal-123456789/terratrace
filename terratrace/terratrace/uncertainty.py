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
    lower bound on uncertainty. For honest, autocorrelation-aware CIs use
    :func:`block_bootstrap_pareto` (the spatial moving-block bootstrap).
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


def block_resample_2d(field, block, rng):
    """Moving-block bootstrap of a 2-D field.

    The output (same shape as ``field``) is tiled with ``block x block`` patches
    drawn with replacement from random positions in the source, so WITHIN-block
    spatial autocorrelation is preserved instead of destroyed. NaNs are carried
    along with their block. A block of 1 degenerates to an independent-pixel
    resample; a block at or above the field's correlation length yields honest
    (wider) uncertainty. Edge blocks are clipped to fit.
    """
    a = np.asarray(field, dtype=float)
    if a.ndim != 2:
        raise ValueError("block_resample_2d needs a 2-D field")
    h, w = a.shape
    b = max(1, int(block))
    b = min(b, h, w)                       # cannot exceed the grid
    out = np.empty_like(a)
    max_oy, max_ox = h - b + 1, w - b + 1  # inclusive top-left origin range
    for ty in range(0, h, b):
        for tx in range(0, w, b):
            oy = int(rng.integers(0, max_oy))
            ox = int(rng.integers(0, max_ox))
            hh, ww = min(b, h - ty), min(b, w - tx)
            out[ty:ty + hh, tx:tx + ww] = a[oy:oy + hh, ox:ox + ww]
    return out


def block_bootstrap_pareto(ref_maps, cand_maps, block=4, n_boot=300, seed=0,
                           extra_dims=None, scales=None):
    """Spatial block-bootstrap version of :func:`bootstrap_pareto`.

    ref_maps / cand_maps carry 2-D feature MAPS for the distributional axes
    (slope/relief/ruggedness) plus a scalar ``connectivity_scalar``. Each
    iteration resamples the reference maps ONCE (paired) and each candidate's maps
    by spatial blocks, so the resulting confidence intervals and non-domination
    frequencies respect spatial autocorrelation rather than assuming independent
    pixels. ``block`` should be at or above the terrain's correlation length.
    Returns the same report shape as bootstrap_pareto, tagged method="block".
    """
    rng = np.random.default_rng(seed)
    extra_dims = extra_dims or {}
    units = list(cand_maps)
    nondom = {u: 0 for u in units}
    winner = {u: 0 for u in units}
    base_samples = {u: [] for u in units}
    for _ in range(n_boot):
        ref_rs = {f: block_resample_2d(ref_maps[f], block, rng).ravel() for f in DIST_FEATURES}
        vecs = {}
        for u in units:
            cm = cand_maps[u]
            base = []
            for f in DIST_FEATURES:
                s = None if scales is None else scales.get(f)
                cand_rs = block_resample_2d(cm[f], block, rng).ravel()
                base.append(normalized_distance(cand_rs, ref_rs[f], scale=s))
            cscale = abs(ref_maps["connectivity_scalar"]) + 1e-6
            conn = abs(cm["connectivity_scalar"] - ref_maps["connectivity_scalar"]) / cscale
            base = tuple(float(x) for x in base)
            base_samples[u].append(base)
            vecs[u] = base + (float(conn),) + tuple(float(x) for x in extra_dims.get(u, ()))
        nd = non_dominated(vecs)
        for u in nd:
            nondom[u] += 1
        if len(nd) == 1:
            winner[next(iter(nd))] += 1
    out = {"n_boot": n_boot, "seed": seed, "method": "block", "block": int(block),
           "note": ("Spatial block bootstrap (block>=correlation length) preserves "
                    "autocorrelation, so these CIs are more honest -- typically WIDER -- "
                    "than the independent-pixel bootstrap. Still an approximation."),
           "units": {}}
    for u in units:
        arr = np.array(base_samples[u])
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
