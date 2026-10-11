"""Scale-resolved analog analysis for TerraTrace.

A single study compares terrain SHAPE at ONE common support. But morphological
similarity is scale-dependent: two surfaces can look alike at a kilometre and
unlike at a hundred metres (or the reverse), and the "best analog" can CHANGE as
the support coarsens. This module turns one support into a SWEEP, answering two
questions a single study cannot:

  * at what spatial scales does a candidate resemble the reference, and
  * does the single best analog change with scale?

It introduces NO new morphology math and takes NO new modelling risk: every
number is produced by re-running the proven comparison core
(:func:`terratrace.study.compare_units`) at each target support with the core
decision lens, and reading the quantities that engine already computes -- each
candidate's core distance vector (``baseline_vectors``) and its Pareto layer
(``frontier.rank``). The only thing added here is the bookkeeping that stacks
those per-support results into a profile and summarises them.

All outputs are plain, JSON-serialisable Python (floats / ints / strings / lists
/ None; ``NaN`` marks an ineligible candidate at a support, matching the engine's
own convention) and are deterministic for deterministic inputs.

Scientific boundary (claim firewall): this is MAP-SCALE TERRAIN-MORPHOLOGY
screening resolved across spatial scales ONLY. "Analog" here means a surface-
shape resemblance at a common support -- it is NOT a traversability, geologic-
equivalence, site-access, resource, or mission-readiness claim, and the per-scale
ordering is a transparent Pareto layering, NOT a composite "likeness" score.
"""
from __future__ import annotations

import math

import numpy as np

from . import study


def scale_profile(raw_units, rights, native_posting_m, reference_id, supports,
                  min_valid=0.5):
    """Profile morphological analog distance + Pareto rank across a scale sweep.

    For each target support ``s`` in ``sorted(supports)`` this runs
    ``study.compare_units(raw_units, rights, native_posting_m, reference_id=...,
    target_support_m=s, min_valid=min_valid, decision_metrics="core")`` and, for
    every candidate (every non-reference id in ``raw_units``), records:

      * ``distance`` -- the candidate's OVERALL core distance to the reference,
        i.e. the L2 norm of its ``baseline_vector`` (``NaN`` if the candidate is
        ineligible / not comparable at that support);
      * ``layer``    -- its Pareto layer from ``frontier.rank`` (1 = best / non-
        dominated), or ``None`` where it is ineligible / unranked.

    Returns a JSON-serialisable dict::

        {"supports": [...ascending...], "reference_id": rid,
         "candidates": [...sorted...],
         "per_candidate": {cid: {"distance": [...], "layer": [...]}},
         "best_by_support": [recommended_unit or None per support],
         "result_by_support": [result_state per support]}

    Morphology-across-scales screening only (see module claim firewall).
    """
    supports = sorted(float(s) for s in supports)
    candidates = sorted(u for u in raw_units if u != reference_id)
    per_candidate = {c: {"distance": [], "layer": []} for c in candidates}
    best_by_support, result_by_support = [], []

    for s in supports:
        pkg = study.compare_units(
            raw_units, rights, native_posting_m, reference_id=reference_id,
            target_support_m=s, min_valid=min_valid, decision_metrics="core")
        bvecs = pkg.get("baseline_vectors", {})
        rank = (pkg.get("frontier") or {}).get("rank", {})
        n_eligible = len(bvecs)
        for c in candidates:
            vec = bvecs.get(c)
            if vec is None:                       # ineligible / blocked / not comparable
                per_candidate[c]["distance"].append(float("nan"))
                per_candidate[c]["layer"].append(None)
                continue
            dist = float(np.linalg.norm(np.asarray(vec, dtype=float)))
            per_candidate[c]["distance"].append(dist if math.isfinite(dist) else float("nan"))
            layer = rank.get(c)
            # frontier is only attached when >= 2 candidates are eligible; a lone
            # eligible candidate is trivially non-dominated -> layer 1.
            if layer is None and n_eligible == 1:
                layer = 1
            per_candidate[c]["layer"].append(int(layer) if layer is not None else None)
        best_by_support.append(pkg.get("recommended_unit"))
        result_by_support.append(pkg.get("result_state"))

    return {
        "supports": supports,
        "reference_id": reference_id,
        "candidates": candidates,
        "per_candidate": per_candidate,
        "best_by_support": best_by_support,
        "result_by_support": result_by_support,
    }


def analog_scale_band(profile, candidate):
    """The band of supports over which ``candidate`` is a layer-1 (non-dominated)
    analog of the reference.

    Returns ``{"supports_layer1": [s where layer == 1],
    "band": (min, max) or None, "fraction_layer1": float}`` -- the explicit list
    of supports at which the candidate is non-dominated, the (min, max) span of
    that list (``None`` if it is never layer 1), and the fraction of swept
    supports at which it is layer 1 (0.0 if there are no supports).
    """
    supports = profile["supports"]
    layers = profile["per_candidate"][candidate]["layer"]
    layer1 = [s for s, lyr in zip(supports, layers) if lyr == 1]
    band = (min(layer1), max(layer1)) if layer1 else None
    fraction = (len(layer1) / len(supports)) if supports else 0.0
    return {"supports_layer1": layer1, "band": band, "fraction_layer1": float(fraction)}


def best_analog_by_scale(profile):
    """The scale-resolved single recommendation: a list of
    ``(support, recommended_unit_or_None)`` pairs, one per swept support, showing
    how the single best analog changes with scale. The unit is ``None`` wherever
    the engine does not reach a lone recommendation (a Pareto TIE or a
    not-comparable / blocked state)."""
    return list(zip(profile["supports"], profile["best_by_support"]))


def scale_profile_signature(profile):
    """A compact, JSON-serialisable summary of a profile.

    Per candidate it reports ``fraction_layer1`` and the layer-1 ``band``; it also
    reports ``scale_stable`` -- ``True`` iff a SINGLE, non-``None`` best analog is
    recommended at EVERY swept support (i.e. the best analog does not change with
    scale and never degrades to a tie). Summary bookkeeping only; carries the same
    morphology-only claim firewall as the module.
    """
    per = {}
    for c in profile["candidates"]:
        band = analog_scale_band(profile, c)
        per[c] = {"fraction_layer1": band["fraction_layer1"], "band": band["band"]}
    best = profile["best_by_support"]
    scale_stable = bool(best) and len(set(best)) == 1 and best[0] is not None
    return {
        "reference_id": profile["reference_id"],
        "supports": profile["supports"],
        "per_candidate": per,
        "scale_stable": bool(scale_stable),
    }
