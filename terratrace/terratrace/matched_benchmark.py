"""Matched-footprint benchmark harness for TerraTrace analog screening.

WHY THIS EXISTS (the scientific defect it corrects). The exploratory real run
compared a Mars MOLA window (~10 deg, ~590 km) against Earth windows (~0.4 deg,
~40 km) -- a ~15x mismatch in physical FOOTPRINT. Morphology descriptors are not
comparable across windows of different physical extent: a larger window contains
longer-wavelength regional relief that a smaller window simply cannot express, so
relief/slope/ruggedness distances conflate *terrain* differences with *window-size*
differences. A resemblance found that way may be an artifact of the extent mismatch
rather than a real morphological analog.

WHAT THIS DOES. It wraps -- it does NOT replace -- the engine's existing
``study.compare_units`` decision (body-aware geometry, common support, multi-lens
Pareto, TIE/INDETERMINATE/NOT_COMPARABLE/BLOCKED). The harness adds exactly two
controls and the provenance to defend them:

  * ``extent_m``  -- the physical side length (metres) each unit is cropped to
                     BEFORE aggregation. Controls which wavelengths are present.
  * ``support_m`` -- the aggregation cell size (metres) passed to compare_units.
                     Controls the smallest resolved feature.

These are varied INDEPENDENTLY so a scale experiment (vary support at fixed extent)
never silently becomes an extent experiment (vary extent at fixed support), and so a
*matched-footprint* comparison (every unit cropped to the same ``extent_m``) can be
contrasted with the original *mismatched* comparison.

It does not upsample: ``effective_resolution_m`` flags any support finer than a few
source pixels, so resampled grid spacing is never read as independent source
resolution. Pure NumPy + the existing engine; deterministic; no network, no rasterio.

Scope / claim firewall (inherited): map-scale terrain-morphology screening only --
not a traversability, geologic-equivalence, site-access, or mission-readiness claim.
"""
from __future__ import annotations

import numpy as np

from . import study

__all__ = [
    "crop_center",
    "effective_resolution_m",
    "cell_provenance",
    "matched_cell",
    "mismatched_cell",
    "extent_support_grid",
    "single_descriptor_baseline",
    "lens_ablation_matched",
    "selection_adjusted_pvalue",
]

_VALID = "verified_allowed"


def _as_map(value, keys):
    """Broadcast a scalar to {key: value}, or pass a dict through unchanged."""
    if isinstance(value, dict):
        return dict(value)
    return {k: value for k in keys}


def crop_center(z, src_spacing_m, extent_m):
    """Centered square crop of ``z`` to a physical side length ``extent_m``.

    ``n = round(extent_m / src_spacing_m)`` pixels per side, clamped to the array
    (so a window larger than the data is truncated, and flagged). Returns
    ``(cropped, info)`` where ``info`` records the requested vs actually-realised
    extent, the pixel count, truncation, and the finite (valid) fraction. NaN-safe;
    never raises on reasonable input.
    """
    z = np.asarray(z, dtype=float)
    src = float(src_spacing_m)
    rows, cols = z.shape
    n_req = int(round(float(extent_m) / src)) if src > 0 else min(rows, cols)
    n_req = max(1, n_req)
    n = min(n_req, rows, cols)
    r0 = (rows - n) // 2
    c0 = (cols - n) // 2
    sub = z[r0:r0 + n, c0:c0 + n]
    finite = int(np.isfinite(sub).sum())
    info = {
        "requested_extent_m": float(extent_m),
        "actual_extent_m": float(n * src),
        "n_pixels": int(n),
        "src_spacing_m": src,
        "truncated": bool(n < n_req),
        "valid_fraction": float(finite / sub.size) if sub.size else 0.0,
    }
    return sub, info


def effective_resolution_m(src_spacing_m, factor=3.0):
    """Finest support (metres) that does NOT fabricate sub-pixel detail.

    A DEM cannot resolve features below a few samples; ``factor * src_spacing``
    (default 3x) is a conservative effective resolving capability. A ``support_m``
    below this is upsampling -- the harness flags it rather than treating the
    resampled grid spacing as independent source resolution.
    """
    return float(factor) * float(src_spacing_m)


def cell_provenance(uid, crop_info, support_m, block_size=4, res_factor=3.0):
    """Provenance for one unit in one (extent, support) cell.

    Records the metadata a reviewer needs to judge comparability: metric
    dimensions, valid area, source spacing + effective resolving capability, the
    common support, the descriptor neighbourhood (support in metres), the number of
    usable spatial blocks at that support, and an explicit upsampling-risk flag.
    """
    src = crop_info["src_spacing_m"]
    eff = effective_resolution_m(src, res_factor)
    n_support_cells = int(crop_info["actual_extent_m"] // float(support_m)) if support_m > 0 else 0
    usable_blocks = int((n_support_cells // int(block_size)) ** 2) if n_support_cells >= block_size else 0
    return {
        "unit": uid,
        "actual_extent_m": crop_info["actual_extent_m"],
        "n_source_pixels": crop_info["n_pixels"],
        "valid_fraction": crop_info["valid_fraction"],
        "src_spacing_m": src,
        "effective_resolution_m": eff,
        "support_m": float(support_m),
        "support_cells_per_side": n_support_cells,
        "usable_blocks": usable_blocks,
        "truncated": crop_info["truncated"],
        "upsampling_risk": bool(float(support_m) < eff),
    }


def _run_compare(cropped, native, rights, reference_id, support_m,
                 decision_metrics, compare_kw):
    """Delegate the actual decision to the engine (preserves all its semantics)."""
    pkg = study.compare_units(
        cropped, rights, native, reference_id=reference_id,
        target_support_m=float(support_m), decision_metrics=decision_metrics,
        **compare_kw)
    frontier = pkg.get("frontier") or {}
    layers = frontier.get("pareto_layers") or [[]]
    out = {
        "result_state": pkg.get("result_state"),
        "recommended_unit": pkg.get("recommended_unit"),
        "pareto_layer1": list(layers[0]),
        # The engine's full BASELINE frontier, passed through unchanged (empty when
        # the engine built none, i.e. fewer than two eligible candidates): every
        # Pareto layer, and the pairwise dominance matrix {"a|b": winner or "~"}
        # over sorted id pairs. Lets callers test relations between candidates.
        "pareto_layers": [list(layer) for layer in (frontier.get("pareto_layers") or [])],
        "dominance_matrix": dict(frontier.get("dominance_matrix") or {}),
        "package_hash": pkg.get("package_hash"),
    }
    # Surface the engine's EXISTING uncertainty when it was requested (we do not
    # build a second statistics system): spatial-block non-domination frequency and
    # the permutation significance of the recommendation vs the runner-up.
    boot = pkg.get("bootstrap") or {}
    bu = boot.get("units") or {}
    if bu:
        out["nondominated_freq"] = {u: bu[u].get("nondominated_freq") for u in bu}
        out["bootstrap_method"] = boot.get("method")
    sig = pkg.get("significance")
    if sig:
        out["significance"] = sig
    return out


def matched_cell(units, src_spacings, reference_id, extent_m, support_m,
                 decision_metrics="core", rights=None, block_size=4,
                 res_factor=3.0, **compare_kw):
    """One MATCHED-footprint cell: every unit cropped to the SAME ``extent_m``.

    Crops each unit centrally to ``extent_m`` at its own source spacing, then hands
    the cropped grids to ``study.compare_units`` at common ``support_m`` under one
    decision lens. Returns the engine outcome plus per-unit provenance and the
    harness controls. This is the comparability-correct comparison.
    """
    keys = list(units)
    src = _as_map(src_spacings, keys)
    rights = _as_map(rights if rights is not None else _VALID, keys)
    cropped, prov = {}, {}
    for uid in keys:
        sub, info = crop_center(units[uid], src[uid], extent_m)
        cropped[uid] = sub
        prov[uid] = cell_provenance(uid, info, support_m, block_size, res_factor)
    out = _run_compare(cropped, src, rights, reference_id, support_m,
                       decision_metrics, compare_kw)
    out.update({"mode": "matched", "extent_m": float(extent_m),
                "support_m": float(support_m), "decision_metrics": decision_metrics,
                "reference_id": reference_id, "provenance": prov})
    return out


def mismatched_cell(units, src_spacings, reference_id, ref_extent_m, cand_extent_m,
                    support_m, decision_metrics="core", rights=None, block_size=4,
                    res_factor=3.0, **compare_kw):
    """One MISMATCHED-footprint cell: the reference is cropped to ``ref_extent_m``
    while every candidate is cropped to ``cand_extent_m`` (ref >> cand reproduces the
    original ~15x footprint confound). Same engine decision; use it ONLY as the
    control to contrast against :func:`matched_cell`.
    """
    keys = list(units)
    src = _as_map(src_spacings, keys)
    rights = _as_map(rights if rights is not None else _VALID, keys)
    cropped, prov = {}, {}
    for uid in keys:
        ext = ref_extent_m if uid == reference_id else cand_extent_m
        sub, info = crop_center(units[uid], src[uid], ext)
        cropped[uid] = sub
        prov[uid] = cell_provenance(uid, info, support_m, block_size, res_factor)
    out = _run_compare(cropped, src, rights, reference_id, support_m,
                       decision_metrics, compare_kw)
    out.update({"mode": "mismatched", "ref_extent_m": float(ref_extent_m),
                "cand_extent_m": float(cand_extent_m), "support_m": float(support_m),
                "decision_metrics": decision_metrics, "reference_id": reference_id,
                "footprint_ratio": float(ref_extent_m) / float(cand_extent_m),
                "provenance": prov})
    return out


def extent_support_grid(units, src_spacings, reference_id, extents, supports,
                        decision_metrics="core", rights=None, **compare_kw):
    """Scale x extent stability grid: run :func:`matched_cell` over every
    (``extent_m``, ``support_m``) pair under one lens. Returns the list of cells --
    the machine-readable backing for an analog STABILITY MAP (where the outcome
    persists, changes, or becomes unsupported). ``extents`` and ``supports`` are
    swept independently so scale and extent never confound each other.
    """
    cells = []
    for ext in extents:
        for sup in supports:
            cells.append(matched_cell(units, src_spacings, reference_id, ext, sup,
                                      decision_metrics=decision_metrics, rights=rights,
                                      **compare_kw))
    return {"reference_id": reference_id, "decision_metrics": decision_metrics,
            "extents_m": [float(e) for e in extents],
            "supports_m": [float(s) for s in supports], "cells": cells}


# --------------------------------------------------------------------------- #
# Baselines / ablations and selection-aware significance (Milestone 2).        #
# These exist to show what the full multi-lens Pareto decision ADDS over naive #
# single-descriptor matching, and to keep significance honest when the winner  #
# is chosen from a pool. They reuse the engine; they do not replace it.        #
# --------------------------------------------------------------------------- #

def _dist1d(ref_vals, cand_vals):
    """Scale-normalised 1-D distribution distance (a Wasserstein-1 proxy).

    Compares two samples by their quantile functions (101 points) and returns the
    mean absolute quantile gap divided by the reference's robust scale (p90-p10), so
    the number is dimensionless and comparable across descriptors. NaN-safe; returns
    ``nan`` if either sample is empty or the reference has no spread.
    """
    r = np.asarray(ref_vals, dtype=float).ravel(); r = r[np.isfinite(r)]
    c = np.asarray(cand_vals, dtype=float).ravel(); c = c[np.isfinite(c)]
    if r.size == 0 or c.size == 0:
        return float("nan")
    q = np.linspace(0.0, 100.0, 101)
    rq = np.percentile(r, q); cq = np.percentile(c, q)
    scale = np.percentile(r, 90) - np.percentile(r, 10)
    if not np.isfinite(scale) or scale <= 0:
        return float("nan")
    return float(np.mean(np.abs(rq - cq)) / scale)


def single_descriptor_baseline(units, src_spacings, reference_id, extent_m, support_m,
                               descriptor="slope", rights=None):
    """Naive baseline: rank candidates by a ONE-descriptor distribution distance to
    the reference, under the SAME matched-footprint + support controls as the full
    decision. ``descriptor`` is 'slope' or 'relief'. Returns {closest, distances,
    descriptor}. Lets us ask whether the multi-lens Pareto decision adds anything
    (discrimination, trade-off, informative abstention) beyond simple roughness."""
    from . import features, support as _sup
    keys = list(units)
    src = _as_map(src_spacings, keys)
    agg = {}
    for uid in keys:
        sub, _info = crop_center(units[uid], src[uid], extent_m)
        factor = max(int(round(float(support_m) / float(src[uid]))), 1)
        a, _rec = _sup.block_aggregate(sub, factor, src[uid], min_valid=0.5)
        agg[uid] = a
    def descr(a, dx):
        if descriptor == "relief":
            return features.relief(a, window=5, alpha=0.0)
        return features.slope_deg(a, dx, dx)
    dref = descr(agg[reference_id], float(support_m))
    dists = {}
    for uid in keys:
        if uid == reference_id:
            continue
        dists[uid] = _dist1d(dref, descr(agg[uid], float(support_m)))
    finite = {u: d for u, d in dists.items() if np.isfinite(d)}
    closest = min(finite, key=finite.get) if finite else None
    return {"descriptor": descriptor, "extent_m": float(extent_m),
            "support_m": float(support_m), "closest": closest, "distances": dists}


def lens_ablation_matched(units, src_spacings, reference_id, extent_m, support_m,
                          lenses=("core", "extended", "geomorphic", "landform",
                                  "texture", "hydro"), rights=None, **compare_kw):
    """Run :func:`matched_cell` under each decision lens at a fixed matched footprint
    and support. Returns {lens: {result_state, recommended_unit, pareto_layer1}} so
    lens agreement/disagreement is explicit (NOT six independent replications)."""
    out = {}
    for lens in lenses:
        c = matched_cell(units, src_spacings, reference_id, extent_m, support_m,
                         decision_metrics=lens, rights=rights, **compare_kw)
        out[lens] = {k: c[k] for k in ("result_state", "recommended_unit", "pareto_layer1")}
    return out


def selection_adjusted_pvalue(p_raw, n_candidates):
    """Selection-aware (Bonferroni) correction for picking the BEST of K candidates.

    When the recommended unit is chosen as the closest of ``n_candidates``, a naive
    per-comparison p-value overstates significance. The adjusted p = min(1, p_raw*K)
    is a deliberately CONSERVATIVE bound on the family-wise error of the selection.
    This does not model spatial dependence by itself; pair it with the engine's
    spatial-block bootstrap (bootstrap_method='block'), which is the primary
    uncertainty treatment. Returns a float in [0, 1]."""
    k = max(1, int(n_candidates))
    p = float(p_raw)
    if not np.isfinite(p):
        return float("nan")
    return float(min(1.0, max(0.0, p) * k))
