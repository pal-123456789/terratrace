"""Three separable verdicts: RANKING, ADEQUACY, and EVIDENCE SUFFICIENCY.

WHY THIS MODULE EXISTS
----------------------
The engine already answers three different questions, and until now nothing forced them to be
*reported* as three different things:

1. **Which candidate is closest, among the candidates tested?** (`decision.non_dominated`,
   `matched_benchmark`, `study.compare_units`). This is a RELATIVE statement. It is well defined
   whenever there is a field of candidates, however bad the field.
2. **Is any candidate actually within the reference's own morphological variability at this
   scale?** (`adequacy.adequacy_assessment`, calibrated from the reference's own held-out
   sub-windows). This is an ABSOLUTE statement about similarity, and it needs a yardstick the data
   can justify. When one cannot be justified, the honest answer is "not established", not a number.
3. **Is the evidence enough to answer either of those?** This is a question about the *evidence*
   rather than about the terrain: how many candidates, how many supports, what fraction of each
   window carried data, whether the adequacy band could be calibrated at all, whether the axes are
   actually independent dimensions, and how large an error ensemble was drawn.

The reason to keep them apart is the project's own history. It withdrew a Mars claim because
"non-dominated among these candidates" had been read as "a good analog", and it published a lunar
page where the survivor at one site is 70 % away on its worst axis -- a definite ranking and no
adequacy at all. Both are the same failure: collapsing (1) into (2). Neither question implies the
other, and an implementation that lets a reader see only one number will keep inviting that
collapse.

THE RULES, WHICH ARE DELIBERATELY MECHANICAL
--------------------------------------------
* **Nothing here computes a composite score.** There is no "analog-ness" number, no weight, and no
  ranking of adequacy. A test asserts that no key in the output looks like a score.
* **Ranking is never *withdrawn* because sufficiency is poor** -- it is marked `provisional`. A
  comparison that was run is a fact about the candidates even when the evidence behind it is thin;
  deleting it would hide what was computed, and hiding it is how a reader concludes nothing.
* **Adequacy is never inferred from ranking.** `not_established` stays `not_established` whatever
  the ranking says, and the structural check below refuses to let a caller mark it otherwise
  without an actual calibrated band.
* **Insufficiency is named, with reasons.** "Insufficient evidence" alone is unfalsifiable; the
  reasons list says which evidence was missing.

SCOPE (inherited, non-negotiable): map-scale terrain-MORPHOLOGY screening only. None of the three
verdicts is a traversability, geologic-equivalence, site-access, or mission-readiness claim, and an
`ESTABLISHED_ADEQUATE` adequacy verdict does not upgrade any of them -- it says a candidate's
descriptor distributions sit inside the reference's own spread at one scale, and nothing more.
"""
from __future__ import annotations

__all__ = [
    "QUESTIONS", "RANKING_STATES", "ADEQUACY_STATES", "SUFFICIENCY_STATES",
    "ranking_verdict", "adequacy_verdict", "sufficiency_verdict", "three_part_verdict",
    "conflation_errors", "SCORE_LIKE_KEYS", "band_discrimination",
]

QUESTIONS = {
    "relative_ranking": "Which candidate is closest, among the candidates tested?",
    "absolute_adequacy": "Is any candidate inside the reference's own morphological variability "
                         "at this scale, on a band the data can justify?",
    "evidence_sufficiency": "Is the evidence enough to answer either of the other two for this "
                            "comparison?",
}

RANKING_STATES = ("RECOMMEND_FOLLOW_UP", "TIE", "INDETERMINATE", "NOT_COMPARABLE", "BLOCKED")
ADEQUACY_STATES = ("NOT_ESTABLISHED", "ESTABLISHED_ADEQUATE", "ESTABLISHED_NONE_ADEQUATE")
SUFFICIENCY_STATES = ("INSUFFICIENT", "MARGINAL", "SUFFICIENT")

# Declared sufficiency rules. Each is a fact about the evidence, not about the terrain.
MIN_CANDIDATES = 3
MIN_SUPPORTS = 3
MIN_VALID_FRACTION = 0.5
MIN_REALISATIONS_FOR_ENSEMBLE_CLAIM = 30

# A composite score is what this project refuses to produce. If any of these appears as a key
# anywhere in a verdict block, something has smuggled one in.
SCORE_LIKE_KEYS = ("score", "composite", "analog_score", "analogness", "analog_ness",
                   "likeness", "similarity_index", "rating", "grade", "overall")


def ranking_verdict(result_state, non_dominated, recommended_unit=None,
                    worst_axis_distance=None, runner_up=None, provisional=False):
    """Part 1: what the field of candidates says. Relative, and nothing else.

    ``worst_axis_distance`` is carried through because it is the number a reader will otherwise
    reconstruct badly: it is a *distance*, reported per-unit, never a quality score.
    """
    state = str(result_state).upper()
    if state not in RANKING_STATES:
        raise ValueError(f"unknown result_state {result_state!r}; known: {RANKING_STATES}")
    return {"question": QUESTIONS["relative_ranking"],
            "state": state,
            "recommended_unit": recommended_unit,
            "layer1": sorted(non_dominated or []),
            "runner_up": runner_up,
            "worst_axis_distance_fraction": worst_axis_distance,
            "provisional": bool(provisional),
            "note": ("Relative to the candidate set tested. A unit can be closest here and still be "
                     "far from the reference; that is what the adequacy part is for.")}


def band_discrimination(controls, thresholds, max_admitted_fraction=0.5):
    """Does a calibrated band actually SEPARATE? Returns the record, and whether it does.

    Why this exists. A band built from a reference's own sub-window variability can be so wide that
    it admits everything -- and a yardstick that says "adequate" to every candidate has established
    nothing while looking like a positive result. The lunar panel is a live example: on its first
    run the band admitted all five OTHER lunar sites, i.e. terrain from demonstrably different
    places, on every descriptor.

    ``controls`` is a list of ``{descriptor: distance}`` for units known NOT to be drawn from the
    reference's population -- terrain that is different for a reason that has nothing to do with the
    candidate set (sibling sites, not the candidates themselves, so the test is not circular).
    ``thresholds`` is ``{descriptor: p95}`` for the descriptors whose band was established.

    A control is ADMITTED when, for every established descriptor, its distance is within that
    descriptor's threshold -- the same rule the adequacy statement uses. The band discriminates when
    at most ``max_admitted_fraction`` of the controls are admitted. The fraction is a parameter so
    that the criterion is visible and can be argued with, rather than buried.
    """
    descs = [d for d, t in (thresholds or {}).items() if np_isfinite(t)]
    if not descs or not controls:
        return {"controls": len(controls or []), "admitted": None, "discriminates": None,
                "max_admitted_fraction": float(max_admitted_fraction),
                "note": "no band and controls to compare, so discrimination was not tested"}
    admitted = []
    for c in controls:
        if all(np_isfinite(c.get(d, float("nan"))) and c[d] <= thresholds[d] for d in descs):
            admitted.append(True)
        else:
            admitted.append(False)
    frac = sum(admitted) / len(admitted)
    return {"controls": len(admitted),
            "admitted": int(sum(admitted)),
            "admitted_fraction": float(frac),
            "thresholds": {d: float(thresholds[d]) for d in descs},
            "max_admitted_fraction": float(max_admitted_fraction),
            "discriminates": bool(frac <= max_admitted_fraction),
            "note": ("the band admits terrain from different places, so it does not separate similar "
                     "from dissimilar here" if frac > max_admitted_fraction
                     else "the band rejects most of the known-different controls")}


def np_isfinite(x):
    """Local NaN test, so this module stays importable without NumPy for the pure parts."""
    try:
        return x == x and x not in (float("inf"), float("-inf"))
    except Exception:
        return False


def adequacy_verdict(assessment=None, discrimination=None):
    """Part 2: is any candidate inside the reference's own variability? Absolute, and yardsticked.

    Consumes an :func:`terratrace.adequacy.adequacy_assessment` result. With no assessment at all
    the answer is NOT_ESTABLISHED with the project's own sentence -- never a guessed number.

    ``discrimination`` is an optional :func:`band_discrimination` record. A band that admits
    known-different terrain is not an adequacy yardstick, so an established band that fails the
    discrimination test is reported as NOT_ESTABLISHED with that reason rather than as a positive
    result. This branch exists because the alternative -- reporting "adequate" for every candidate
    of a panel whose siblings also pass -- is the exact false positive this project keeps finding.
    """
    from . import adequacy as _ade
    if assessment is None or not assessment.get("established"):
        return {"question": QUESTIONS["absolute_adequacy"],
                "state": "NOT_ESTABLISHED",
                "adequate_candidates": [],
                "band": None,
                "discrimination": discrimination,
                "note": _ade.NOT_ESTABLISHED_NOTE}
    if discrimination is not None and discrimination.get("discriminates") is False:
        return {"question": QUESTIONS["absolute_adequacy"],
                "state": "NOT_ESTABLISHED",
                "adequate_candidates": [],
                "band": {d: {"median": b["band"]["median"], "p95": b["band"]["p95"]}
                         for d, b in (assessment.get("per_descriptor") or {}).items()
                         if b.get("established")},
                "discrimination": discrimination,
                "note": (_ade.NOT_ESTABLISHED_NOTE + " A band was calibrated, but it admits "
                         f"{discrimination.get('admitted')} of {discrimination.get('controls')} "
                         "control units that are known to be different terrain, so membership in it "
                         "is not evidence of similarity at this scale.")}
    return {"question": QUESTIONS["absolute_adequacy"],
            "state": ("ESTABLISHED_ADEQUATE" if assessment.get("any_adequate")
                      else "ESTABLISHED_NONE_ADEQUATE"),
            "adequate_candidates": list(assessment.get("adequate_candidates") or []),
            "band": {d: {"median": b["band"]["median"], "p95": b["band"]["p95"]}
                     for d, b in (assessment.get("per_descriptor") or {}).items()
                     if b.get("established")},
            "discrimination": discrimination,
            "note": _ade.ESTABLISHED_NOTE}


def sufficiency_verdict(n_candidates, n_supports, min_valid_fraction,
                        adequacy_band_established=False, effective_rank=None,
                        n_realisations=None, ensemble_claim=False, extra_reasons=()):
    """Part 3: is the evidence enough? About the evidence, not about the terrain.

    INSUFFICIENT when the comparison barely exists: fewer than :data:`MIN_CANDIDATES` candidates,
    fewer than two supports, or a window whose valid coverage is below
    :data:`MIN_VALID_FRACTION`. MARGINAL when it exists but something declared as load-bearing is
    missing or weak: fewer than :data:`MIN_SUPPORTS` supports, no adequacy band, an error ensemble
    smaller than :data:`MIN_REALISATIONS_FOR_ENSEMBLE_CLAIM` while an ensemble is being claimed, or
    axes that span a single dimension so the evidence is one-dimensional whatever the axis count
    says. SUFFICIENT otherwise.

    Every reason is returned, so "insufficient" is a claim that can be checked rather than a mood.
    """
    reasons = list(extra_reasons)
    if n_candidates < MIN_CANDIDATES:
        reasons.append(f"{n_candidates} candidate(s) compared; fewer than {MIN_CANDIDATES} is not "
                       f"a field to rank within")
    if n_supports < 2:
        reasons.append(f"{n_supports} support(s) evaluated; a scale-stable statement needs at least 2")
    if min_valid_fraction < MIN_VALID_FRACTION:
        reasons.append(f"valid coverage {min_valid_fraction:.3f} is below {MIN_VALID_FRACTION}")
    if reasons:
        state = "INSUFFICIENT"
        return {"question": QUESTIONS["evidence_sufficiency"], "state": state,
                "reasons": reasons, "n_candidates": int(n_candidates),
                "n_supports": int(n_supports),
                "min_valid_fraction": float(min_valid_fraction),
                "effective_rank": effective_rank,
                "n_realisations": n_realisations}

    if n_supports < MIN_SUPPORTS:
        reasons.append(f"{n_supports} supports; {MIN_SUPPORTS} or more is needed before a scale "
                       f"statement is more than a single-scale result")
    if not adequacy_band_established:
        reasons.append("no adequacy band could be calibrated, so the absolute question cannot be "
                       "answered from this data")
    if ensemble_claim and (n_realisations or 0) < MIN_REALISATIONS_FOR_ENSEMBLE_CLAIM:
        reasons.append(f"{n_realisations} error realisations sampled while an ensemble claim is "
                       f"made; fewer than {MIN_REALISATIONS_FOR_ENSEMBLE_CLAIM}")
    if effective_rank is not None and effective_rank <= 1:
        reasons.append("the axes span a single dimension, so the evidence is one-dimensional "
                       "whatever the axis count suggests")

    return {"question": QUESTIONS["evidence_sufficiency"],
            "state": "MARGINAL" if reasons else "SUFFICIENT",
            "reasons": reasons,
            "n_candidates": int(n_candidates),
            "n_supports": int(n_supports),
            "min_valid_fraction": float(min_valid_fraction),
            "effective_rank": effective_rank,
            "n_realisations": n_realisations}


def three_part_verdict(ranking, adequacy, sufficiency):
    """Compose the three, keeping them visibly separate. Does not merge, weight, or rank them."""
    v = {"questions": dict(QUESTIONS),
         "relative_ranking": dict(ranking),
         "absolute_adequacy": dict(adequacy),
         "evidence_sufficiency": dict(sufficiency),
         "separable": True,
         "reading": ("These are three answers to three different questions. A definite ranking with "
                     "NOT_ESTABLISHED adequacy is a normal, expected outcome -- it means the "
                     "shortlist is ordered and nothing on it has been shown to be a good analog.")}
    problems = conflation_errors(v)
    if problems:
        raise ValueError("the verdict block conflates what it must keep apart: "
                         + "; ".join(problems))
    return v


def conflation_errors(verdict):
    """Structural checks on a composed verdict. Returns a list of problems; empty means clean.

    These are deliberately mechanical rather than rhetorical. They catch: a missing part (silence
    about adequacy is how ranking gets read as adequacy); a composite score smuggled in anywhere;
    an adequacy state asserted without a calibrated band; a recommended unit absent from its own
    layer-1 set; and a sufficiency state that is not one of the declared three.
    """
    problems = []
    for key in QUESTIONS:
        if key not in verdict:
            problems.append(f"{key} is missing, so the other two will be read as covering it")
    if problems:
        return problems

    def walk(o, path=""):
        if isinstance(o, dict):
            for k, v in o.items():
                yield path + "/" + str(k)
                yield from walk(v, path + "/" + str(k))
        elif isinstance(o, (list, tuple)):
            for i, v in enumerate(o):
                yield from walk(v, f"{path}[{i}]")

    for path in walk(verdict):
        leaf = path.rsplit("/", 1)[-1].lower().strip("[]0123456789")
        if leaf in SCORE_LIKE_KEYS:
            problems.append(f"a composite score is present at {path}; this project ranks by Pareto "
                            f"dominance and reports adequacy separately, never as one number")

    ade = verdict["absolute_adequacy"]
    if ade.get("state") not in ADEQUACY_STATES:
        problems.append(f"unknown adequacy state {ade.get('state')!r}")
    if ade.get("state", "").startswith("ESTABLISHED") and not ade.get("band"):
        problems.append("adequacy is asserted as ESTABLISHED with no calibrated band reported")

    suf = verdict["evidence_sufficiency"]
    if suf.get("state") not in SUFFICIENCY_STATES:
        problems.append(f"unknown sufficiency state {suf.get('state')!r}")

    rank = verdict["relative_ranking"]
    if rank.get("state") not in RANKING_STATES:
        problems.append(f"unknown ranking state {rank.get('state')!r}")
    rec = rank.get("recommended_unit")
    if rec is not None and rec not in (rank.get("layer1") or []):
        problems.append(f"the recommended unit {rec!r} is not in its own non-dominated set, so the "
                        f"two fields disagree about the same comparison")
    if rank.get("state") != "RECOMMEND_FOLLOW_UP" and rec is not None:
        problems.append(f"state {rank.get('state')} with a recommended unit {rec!r}")
    return problems
