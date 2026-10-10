"""Decision-sensitivity / ablation reporting.

This module answers one narrow question about an *already produced* study:
"does the recommendation survive changing the decision lens and the common
support?" It drives the real engine via :func:`terratrace.study.compare_units`
once per setting and tabulates whether the recommended unit stays the same.

Scientific boundary (unchanged): this is map-scale terrain-morphology
screening only. Nothing here produces a rover, traversability, geologic-
equivalence, access, or mission-readiness claim. An ablation is a *robustness
diagnostic* over the existing morphology screen -- it adds no new scientific
claim, it only reports how fragile or stable the existing one is.
"""
from __future__ import annotations

from . import study

RECOMMEND_STATE = "RECOMMEND_FOLLOW_UP"


def _summarize(entries):
    """Shared stability rule for a set of ablation runs.

    entries: iterable of (result_state, recommended_unit).

    Returns (recommended_units, recommendation_stable, n_recommend) where
    recommended_units is the sorted set of non-None recommendations (which, by
    the engine's contract, are exactly those from RECOMMEND_FOLLOW_UP runs),
    recommendation_stable is True when that set has size <= 1 (all recommending
    runs name the same unit, or none recommends), and n_recommend is how many
    runs recommended a unit.
    """
    entries = list(entries)
    recs = sorted({rec for (state, rec) in entries
                   if state == RECOMMEND_STATE and rec is not None})
    n_recommend = sum(1 for (state, rec) in entries
                      if state == RECOMMEND_STATE and rec is not None)
    return recs, len(recs) <= 1, n_recommend


def lens_ablation(raw_units, rights, native_posting_m, reference_id,
                  target_support_m=100.0, min_valid=0.5,
                  lenses=("core", "extended", "geomorphic")):
    """Re-run the screen under each decision lens at a fixed common support.

    Reports whether every lens that reaches RECOMMEND_FOLLOW_UP names the same
    unit (recommendation_stable), the sorted set of recommended units, and how
    many lenses recommended.
    """
    per_lens = {}
    for lens in lenses:
        pkg = study.compare_units(
            raw_units, rights, native_posting_m, reference_id=reference_id,
            target_support_m=target_support_m, min_valid=min_valid,
            decision_metrics=lens)
        per_lens[lens] = {"result_state": pkg["result_state"],
                          "recommended_unit": pkg["recommended_unit"]}

    recs, stable, n_recommend = _summarize(
        (v["result_state"], v["recommended_unit"]) for v in per_lens.values())
    return {"per_lens": per_lens,
            "recommended_units": recs,
            "recommendation_stable": stable,
            "n_recommend": n_recommend}


def support_ablation(raw_units, rights, native_posting_m, reference_id, supports,
                     decision_metrics="core", min_valid=0.5):
    """Re-run the screen at each common support (target_support_m) under one lens.

    Same stability rule as :func:`lens_ablation`: stable when every support that
    reaches RECOMMEND_FOLLOW_UP names the same unit.
    """
    per_support = {}
    for s in supports:
        pkg = study.compare_units(
            raw_units, rights, native_posting_m, reference_id=reference_id,
            target_support_m=float(s), min_valid=min_valid,
            decision_metrics=decision_metrics)
        per_support[s] = {"state": pkg["result_state"],
                          "recommended": pkg["recommended_unit"]}

    recs, stable, n_recommend = _summarize(
        (v["state"], v["recommended"]) for v in per_support.values())
    return {"per_support": per_support,
            "recommended_units": recs,
            "recommendation_stable": stable,
            "n_recommend": n_recommend,
            "decision_metrics": decision_metrics}


def ablation_report(raw_units, rights, native_posting_m, reference_id,
                    target_support_m=100.0, supports=None, min_valid=0.5):
    """Combined robustness ablation over decision lens and (optionally) support.

    Runs :func:`lens_ablation` at ``target_support_m`` and, when ``supports`` is
    given, :func:`support_ablation` across those supports. ``overall_stable`` is
    True iff the lens recommendation is stable AND (support is stable OR no
    support ablation was requested). This is a robustness diagnostic over the
    map-scale morphology screen, not a new scientific claim.
    """
    lens = lens_ablation(
        raw_units, rights, native_posting_m, reference_id,
        target_support_m=target_support_m, min_valid=min_valid)

    sup = None
    if supports is not None:
        sup = support_ablation(
            raw_units, rights, native_posting_m, reference_id, supports,
            decision_metrics="core", min_valid=min_valid)

    lens_stable = lens["recommendation_stable"]
    support_stable = sup["recommendation_stable"] if sup is not None else True
    overall_stable = bool(lens_stable and support_stable)

    if sup is None:
        support_clause = "support ablation skipped"
    else:
        support_clause = (f"support-stable={sup['recommendation_stable']} across "
                          f"supports {sorted(float(s) for s in supports)}")
    note = ("Robustness ablation (not a new claim): the same map-scale morphology "
            "screen re-run across decision lenses and common supports. "
            f"lens-stable={lens_stable}; {support_clause}; "
            f"overall_stable={overall_stable}.")

    return {"lens": lens,
            "support": sup,
            "overall_stable": overall_stable,
            "note": note}
