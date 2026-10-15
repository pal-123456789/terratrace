"""Relative-vs-absolute morphological ADEQUACY, calibrated from the reference's
own internal variability (TerraTrace Capability 6A).

WHY THIS EXISTS (the defect it corrects). The engine's selection decision
(``study.compare_units`` -> body-aware geometry, common support, multi-lens
Pareto) answers exactly one question: *which candidate is the best analog AMONG
THESE candidates*. A candidate can be non-dominated -- the "winner" -- while
every candidate is in truth a poor morphological match. "Best among these" is
not the same as "actually similar". This module adds the SECOND, orthogonal
question: is a candidate within a defensible morphological SIMILARITY RANGE of
the reference at this scale, or is it merely the least-bad of a bad field?

WHAT IT DELIBERATELY DOES NOT DO. It does not invent a universal analog score and
it does not rank. There is no body-independent "analog-ness" constant to score
against; inventing one would be false precision. Instead adequacy is defined
RELATIVE TO THE REFERENCE'S OWN VARIABILITY: how different is the reference from
ITSELF, measured on held-out sub-windows of the same reference at the same
scale? That self-distance band is the only honest yardstick the data supply, and
when the reference window is too small to build it, the method says so rather
than guessing.

METHOD (calibrate from internal self-distance).
  1. Split the reference window into ``n_split`` x ``n_split`` non-overlapping
     sub-windows (held-out tiles of the SAME reference).
  2. Aggregate each sub-window to the common analysis ``support_m`` and reduce it
     to a small descriptor set (slope and/or relief).
  3. Compute the pairwise scale-normalised distribution distances
     (``matched_benchmark._dist1d``) AMONG those sub-windows: the reference's
     INTERNAL self-distance band -- how far the reference sits from itself at
     this scale and footprint.
  4. A candidate is ADEQUATE for a descriptor if its distance-to-reference is
     within that band (``distance <= band quantile``; frozen at the 95th
     percentile). Otherwise it is INADEQUATE -- outside the reference's own
     morphological variability.
  5. If the window cannot be split into >= 3 usable sub-windows the band cannot
     be calibrated and ABSOLUTE ADEQUACY IS NOT ESTABLISHED (reported honestly;
     no number is fabricated).

The band is estimated on sub-windows (smaller, noisier samples) while a
candidate's distance uses the full matched footprint (larger, steadier sample),
so the yardstick is deliberately CONSERVATIVE -- a genuine same-texture candidate
falls inside it; a poor match falls well outside.

Frozen, documented defaults: ``quantile=95.0``, ``n_split=3``. Pure NumPy,
deterministic, NaN-safe, JSON-serialisable, no network.

Scope / claim firewall (inherited): map-scale terrain-MORPHOLOGY screening only
-- not a traversability, geologic-equivalence, site-access, or mission-readiness
claim. "Best among candidates" (Pareto non-domination, computed elsewhere) and
"adequate relative to the reference's own variability" (here) are DIFFERENT
questions; this module answers only the second.
"""
from __future__ import annotations

import numpy as np

from . import features, support
from .matched_benchmark import _dist1d, crop_center

__all__ = [
    "reference_internal_band",
    "adequacy_assessment",
    "QUANTILE_DEFAULT",
    "N_SPLIT_DEFAULT",
    "NOT_ESTABLISHED_NOTE",
    "ESTABLISHED_NOTE",
]

# Frozen, documented defaults for the method.
QUANTILE_DEFAULT = 95.0
N_SPLIT_DEFAULT = 3
_MIN_SUBTILES = 3          # fewer usable sub-windows -> band cannot be calibrated

NOT_ESTABLISHED_NOTE = "Absolute morphological adequacy has not been established."
ESTABLISHED_NOTE = (
    "Adequacy is assessed RELATIVE to the reference's own internal morphological "
    "variability at this scale -- not a universal analog score, and distinct from "
    "'best among candidates' (Pareto non-domination, computed elsewhere)."
)


def _spacing(src_spacings, uid):
    """Resolve a per-unit source spacing from a scalar or a {uid: metres} map."""
    if isinstance(src_spacings, dict):
        return float(src_spacings[uid])
    return float(src_spacings)


def _split_tiles(z, n_split):
    """Yield the ``n_split`` x ``n_split`` non-overlapping sub-tiles of ``z``.

    The edge remainder (rows/cols beyond ``n_split`` whole tiles) is trimmed so
    every sub-tile has the same shape. Yields nothing when ``z`` is too small to
    hold even a 1-pixel tile per split.
    """
    z = np.asarray(z, dtype=float)
    rows, cols = z.shape
    k = int(n_split)
    rstep = rows // k
    cstep = cols // k
    if rstep < 1 or cstep < 1:
        return
    for i in range(k):
        for j in range(k):
            yield z[i * rstep:(i + 1) * rstep, j * cstep:(j + 1) * cstep]


def _aggregate(z, support_m, src_spacing_m):
    """Block-aggregate ``z`` to the common analysis ``support_m`` (integer factor)."""
    factor = max(int(round(float(support_m) / float(src_spacing_m))), 1)
    agg, _rec = support.block_aggregate(np.asarray(z, dtype=float), factor,
                                        float(src_spacing_m), min_valid=0.5)
    return agg


def _descriptor_sample(agg_grid, support_m, descriptor):
    """Finite 1-D descriptor sample from an already-aggregated grid.

    ``descriptor`` is 'slope' (slope magnitude in degrees) or 'relief' (5-window
    max-minus-min). Returns a flat array of the finite values, or an EMPTY array
    when the grid is too small to evaluate the descriptor -- so the caller can
    treat the tile as unusable rather than crash. NaN-safe.
    """
    a = np.asarray(agg_grid, dtype=float)
    if a.ndim != 2 or min(a.shape) < 2:        # too small for a 2-D gradient
        return np.array([], dtype=float)
    if descriptor == "relief":
        d = features.relief(a, window=5, alpha=0.0)
    elif descriptor == "slope":
        d = features.slope_deg(a, float(support_m), float(support_m))
    else:
        raise ValueError(f"unknown descriptor {descriptor!r} (use 'slope' or 'relief')")
    d = np.asarray(d, dtype=float).ravel()
    return d[np.isfinite(d)]


def _internal_self_distances(ref_grid, support_m, src_spacing_m, n_split, descriptor):
    """Pairwise self-distances among the reference's own sub-windows.

    Splits ``ref_grid`` into sub-tiles, aggregates each to ``support_m``, reduces
    each to the ``descriptor`` sample, and returns ``(distances, n_usable)`` where
    ``distances`` is the array of finite pairwise ``_dist1d`` values over the
    upper triangle and ``n_usable`` is how many sub-tiles produced a non-empty
    descriptor sample. Deterministic; non-finite pairs are dropped.
    """
    samples = []
    for sub in _split_tiles(ref_grid, n_split):
        s = _descriptor_sample(_aggregate(sub, support_m, src_spacing_m),
                               support_m, descriptor)
        if s.size > 0:
            samples.append(s)
    n = len(samples)
    dists = []
    for i in range(n):
        for j in range(i + 1, n):
            d = _dist1d(samples[i], samples[j])
            if np.isfinite(d):
                dists.append(float(d))
    return np.asarray(dists, dtype=float), n


def reference_internal_band(ref_grid, support_m, src_spacing_m, n_split=N_SPLIT_DEFAULT,
                            descriptor="slope"):
    """Reference's INTERNAL self-distance band for one descriptor.

    Splits ``ref_grid`` into ``n_split`` x ``n_split`` held-out sub-windows,
    aggregates each to ``support_m``, and measures the pairwise scale-normalised
    distribution distances among them -- how different the reference is from
    itself at this scale. Returns
    ``{"n_subtiles": int, "median": float, "p95": float, "established": bool}``.

    ``established`` is False (and median/p95 are NaN) when fewer than three usable
    sub-windows are available -- i.e. the window is too small to calibrate a band,
    so no absolute statement can be made. ``p95`` is the frozen 95th percentile of
    the self-distances (the default adequacy threshold).
    """
    dists, n = _internal_self_distances(ref_grid, support_m, src_spacing_m,
                                        n_split, descriptor)
    if n < _MIN_SUBTILES or dists.size == 0:
        return {"n_subtiles": int(n), "median": float("nan"),
                "p95": float("nan"), "established": False}
    return {"n_subtiles": int(n),
            "median": float(np.median(dists)),
            "p95": float(np.percentile(dists, 95.0)),
            "established": True}


def adequacy_assessment(units, src_spacings, reference_id, extent_m, support_m,
                        descriptors=("slope", "relief"), quantile=QUANTILE_DEFAULT,
                        n_split=N_SPLIT_DEFAULT, rights=None):
    """Assess ABSOLUTE adequacy of every candidate against the reference's own
    internal variability, at a matched footprint and common support.

    Every unit is cropped to ``extent_m`` and aggregated to ``support_m``. For
    each descriptor the reference's internal self-distance band is calibrated
    (:func:`reference_internal_band`) and each candidate's distance-to-reference
    is measured; the candidate is adequate for that descriptor when the distance
    is within the band (``distance <= band quantile``; ``quantile`` frozen at
    95.0). A candidate is OVERALL adequate when it is adequate on every descriptor
    whose band could be established.

    ``rights`` is accepted for API symmetry with the engine but is NOT used here:
    adequacy is a pure morphological-distance calibration; rights gate the
    engine's *selection* decision elsewhere, not this absolute yardstick.

    Returns a JSON-serialisable, deterministic dict::

        {"established": bool,
         "per_descriptor": {desc: {"band": {"median","p95"}, "established": bool,
                                   "candidates": {cid: {"distance","adequate","ratio"}}}},
         "adequate_candidates": [cid, ...],
         "any_adequate": bool,
         "note": str}

    When no descriptor band can be established (e.g. the window is too small to
    split into >= 3 usable sub-windows) ``established`` is False and ``note`` is
    exactly "Absolute morphological adequacy has not been established."
    """
    keys = list(units)
    if reference_id not in units:
        raise KeyError(f"reference_id {reference_id!r} not in units")
    cand_ids = [u for u in keys if u != reference_id]

    # Matched footprint + common support for every unit (ref included).
    cropped, agg = {}, {}
    for uid in keys:
        sub, _info = crop_center(units[uid], _spacing(src_spacings, uid), extent_m)
        cropped[uid] = sub
        agg[uid] = _aggregate(sub, support_m, _spacing(src_spacings, uid))

    q = float(quantile)
    ref_spacing = _spacing(src_spacings, reference_id)
    per_descriptor = {}
    established_descs = []
    for desc in descriptors:
        # The reference's own internal self-distance band at this scale/footprint.
        dists, n = _internal_self_distances(cropped[reference_id], support_m,
                                            ref_spacing, n_split, desc)
        band_ok = bool(n >= _MIN_SUBTILES and dists.size > 0)
        thr = float(np.percentile(dists, q)) if band_ok else float("nan")
        med = float(np.median(dists)) if band_ok else float("nan")

        dref = _descriptor_sample(agg[reference_id], support_m, desc)
        cand_entries = {}
        for cid in cand_ids:
            dist = _dist1d(dref, _descriptor_sample(agg[cid], support_m, desc))
            finite = bool(np.isfinite(dist))
            ratio = float(dist / thr) if (band_ok and finite and thr > 0) else float("nan")
            adequate = bool(band_ok and finite and dist <= thr)
            cand_entries[str(cid)] = {
                "distance": float(dist) if finite else float("nan"),
                "adequate": adequate,
                "ratio": ratio,
            }
        per_descriptor[str(desc)] = {
            "band": {"median": med, "p95": thr},
            "established": band_ok,
            "candidates": cand_entries,
        }
        if band_ok:
            established_descs.append(str(desc))

    established = len(established_descs) > 0
    adequate_candidates = []
    if established:
        for cid in cand_ids:
            if all(per_descriptor[d]["candidates"][str(cid)]["adequate"]
                   for d in established_descs):
                adequate_candidates.append(str(cid))
    any_adequate = len(adequate_candidates) > 0

    return {
        "established": established,
        "reference_id": str(reference_id),
        "extent_m": float(extent_m),
        "support_m": float(support_m),
        "quantile": q,
        "n_split": int(n_split),
        "descriptors": [str(d) for d in descriptors],
        "per_descriptor": per_descriptor,
        "adequate_candidates": adequate_candidates,
        "any_adequate": any_adequate,
        "note": ESTABLISHED_NOTE if established else NOT_ESTABLISHED_NOTE,
    }
