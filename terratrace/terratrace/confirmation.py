"""Confirmation + specificity REFERENCE PANEL for matched-footprint analog screening.

WHY THIS EXISTS (the two questions a single-reference result cannot answer). An
exploratory matched-footprint run found one Earth candidate to be the closest
morphological match to ONE Mars reference. Whether that means anything depends on
two further questions, which this module answers mechanically:

  * CONFIRMATION -- does the same relationship hold for OTHER, held-out references
    of the same kind (e.g. other volcanic plains) that were NOT used to form the
    hypothesis?
  * SPECIFICITY  -- does it FAIL for references of a DIFFERENT kind (e.g. rugged
    cratered highlands, canyon walls)? If the same candidate is the most-recommended
    unit for every class of reference, the result is NON-SPECIFIC: it reflects that
    candidate being generically closest within a weak shortlist, and must not be
    presented as an analog relationship.

WHAT IT DOES. For every panel reference it compares that reference against the
candidate set ONLY -- never against another panel reference (no same-body
cross-contamination) -- via :func:`matched_benchmark.matched_cell` at each analysis
support, and (optionally) calibrates absolute adequacy via
:func:`adequacy.adequacy_assessment`. Each reference carries a PREDECLARED
expectation (``recommends`` / ``non_dominated`` / ``not_sole`` a named candidate),
frozen before results are seen, and an ``exploratory`` / ``confirmatory`` status.
The module EVALUATES outcomes against those expectations; it never edits, relaxes,
or re-derives them. A failing cell is recorded as ``result_state == "ERROR"`` with
its message and the rest of the panel still runs.

CANDIDATE CLASSES (optional). Hypotheses can also be about CLASSES of candidates
(e.g. "a basaltic candidate Pareto-dominates every smooth non-volcanic control").
Given ``candidate_classes`` ({candidate_id: class_name}), two further expectation
types are available:

  * ``class_in_layer1``  -- some candidate of ``class`` is in the first Pareto layer;
  * ``class_dominates``  -- SOME candidate of ``winner_class`` Pareto-dominates EVERY
    candidate of ``loser_class`` (one winner must beat all losers; a loser absent
    from the dominance matrix, e.g. ineligible, counts as NOT dominated).

Both read the engine's BASELINE Pareto relations at each support (``pareto_layer1``
and the pairwise ``dominance_matrix`` that every cell now carries), so they are
independent of the engine's stability-filtered recommendation state: a TIE or
INDETERMINATE cell can still satisfy them. A reference may also carry several
NAMED expectations (``expects``), each evaluated the same way and reported under
``expectations``; the single ``expect`` and the summary/specificity logic are
unchanged by them.

HONEST LIMITS (stated, not hidden).
  * Replication across references that share one DEM source (same instrument, same
    processing chain) is NOT fully independent evidence; agreement among them is
    weaker than agreement across independent sources.
  * EXPLORATORY references (those that formed or informed the hypothesis) are NEVER
    counted as confirmation; outcomes are reported split by status.
  * ``n_comparisons`` (= references x supports) is reported for multiple-comparison
    awareness; no correction is applied to the outcome counts.
  * A "specific" verdict is a NECESSARY, not sufficient, condition for an analog
    relationship. Specificity is not evaluable without >= 2 reference classes, nor
    when no reference produced any recommendation (there is then no relationship
    whose specificity could be assessed).

Pure (NumPy + the existing engine), deterministic, JSON-serialisable; no network.

Scope / claim firewall (inherited): map-scale terrain-MORPHOLOGY screening only --
not a traversability, geologic-equivalence, process, site-access, or
mission-readiness claim.
"""
from __future__ import annotations

import copy

from . import adequacy as _adequacy
from . import matched_benchmark as _mb

__all__ = [
    "run_reference_panel",
    "evaluate_expectation",
    "STATUSES",
    "EXPECT_TYPES",
    "CLASS_EXPECT_TYPES",
    "OUTCOMES",
    "RECOMMEND",
    "ERROR_STATE",
    "PANEL_NOTE",
]

STATUSES = ("exploratory", "confirmatory")
CLASS_EXPECT_TYPES = ("class_in_layer1", "class_dominates")
EXPECT_TYPES = ("recommends", "non_dominated", "not_sole") + CLASS_EXPECT_TYPES
OUTCOMES = ("holds", "mixed", "fails", "not_predeclared")
RECOMMEND = "RECOMMEND_FOLLOW_UP"
ERROR_STATE = "ERROR"

PANEL_NOTE = (
    "Map-scale terrain-morphology screening only -- not a traversability, "
    "geologic-equivalence, process, site-access, or mission-readiness claim. Each "
    "reference is compared against the candidate set only (never against another "
    "panel reference). Outcomes are evaluated against expectations PREDECLARED "
    "before results were seen and are never adjusted. Exploratory references are "
    "never counted as confirmation. Replication across references sharing one DEM "
    "source is not fully independent (shared instrument/processing). n_comparisons "
    "is reported for multiple-comparison awareness; no correction is applied. A "
    "'specific' verdict is necessary, not sufficient, for an analog relationship."
)

_OPTIONAL_CELL_KEYS = ("nondominated_freq", "bootstrap_method", "significance")


def _sub_map(value, keys):
    """Restrict a {uid: value} map to ``keys``; pass scalars / None through."""
    if isinstance(value, dict):
        return {k: value[k] for k in keys}
    return value


def _check_class_map(candidate_classes, cands):
    """Validate ``candidate_classes`` and restrict it to ``cands`` (None -> None).

    Every candidate needs a non-empty str class; entries for ids outside ``cands``
    are ignored (the returned, stored map holds exactly the candidates used)."""
    if candidate_classes is None:
        return None
    if not isinstance(candidate_classes, dict):
        raise ValueError("candidate_classes must be a {candidate_id: class_name} dict")
    missing = [c for c in cands if c not in candidate_classes]
    if missing:
        raise ValueError(f"candidate_classes has no class for candidate(s) {missing!r}")
    for c in cands:
        cls = candidate_classes[c]
        if not isinstance(cls, str) or not cls:
            raise ValueError(f"candidate {c!r}: class must be a non-empty str, got {cls!r}")
    return {c: candidate_classes[c] for c in cands}


def _check_class_expect(where, exp, classes):
    """A class expectation needs ``candidate_classes`` and must name known classes."""
    kind = exp["type"]
    if classes is None:
        raise ValueError(f"{where}: expectation type {kind!r} needs candidate_classes")
    known = sorted(set(classes.values()))
    fields = ("class",) if kind == "class_in_layer1" else ("winner_class", "loser_class")
    for f in fields:
        if exp.get(f) not in known:
            raise ValueError(f"{where}: {f} {exp.get(f)!r} is not a candidate class "
                             f"(known: {known})")
    if kind == "class_dominates" and exp["winner_class"] == exp["loser_class"]:
        raise ValueError(f"{where}: winner_class and loser_class must differ")


def _check_expect(where, exp, cands, classes):
    """Validate one predeclared expectation; ``where`` prefixes the error."""
    if not isinstance(exp, dict) or exp.get("type") not in EXPECT_TYPES:
        raise ValueError(f"{where} must be None or "
                         f"{{'type': one of {EXPECT_TYPES}, ...}}")
    if exp["type"] in CLASS_EXPECT_TYPES:
        _check_class_expect(where, exp, classes)
    elif exp.get("unit") not in cands:
        raise ValueError(f"{where}: expected unit {exp.get('unit')!r} "
                         f"is not in candidate_ids")


def _validate(grids, spacings, panel, candidate_ids, supports, rights,
              candidate_classes=None):
    """Fail LOUDLY on a malformed predeclaration, before any result is computed.

    Spec errors (unknown status/type, an expectation naming a non-candidate or an
    unknown candidate class, a class expectation without ``candidate_classes``, a
    duplicate expectation name, a panel reference that is also a candidate) are
    programmer errors, not cell failures: they must never be silently absorbed into
    an ERROR outcome. Returns the validated candidate-class map (or None).
    """
    cands = list(candidate_ids)
    if not cands:
        raise ValueError("candidate_ids must be non-empty")
    if len(set(cands)) != len(cands):
        raise ValueError(f"duplicate candidate ids: {cands!r}")
    if not supports:
        raise ValueError("supports must be non-empty")
    for s in supports:
        if not float(s) > 0:
            raise ValueError(f"supports must be positive metres, got {s!r}")
    if not panel:
        raise ValueError("panel must contain at least one reference")
    classes = _check_class_map(candidate_classes, cands)
    ids = []
    for entry in panel:
        rid = entry.get("id")
        if rid is None:
            raise ValueError(f"panel entry without 'id': {entry!r}")
        ids.append(rid)
        cls = entry.get("class")
        if not isinstance(cls, str) or not cls:
            raise ValueError(f"reference {rid!r}: 'class' must be a non-empty str")
        if entry.get("status") not in STATUSES:
            raise ValueError(f"reference {rid!r}: 'status' must be one of {STATUSES}, "
                             f"got {entry.get('status')!r}")
        exp = entry.get("expect")
        if exp is not None:
            _check_expect(f"reference {rid!r}: 'expect'", exp, cands, classes)
        exps = entry.get("expects")
        if exps is not None:
            if not isinstance(exps, (list, tuple)):
                raise ValueError(f"reference {rid!r}: 'expects' must be a list of "
                                 f"named expectations")
            names = []
            for e in exps:
                name = e.get("name") if isinstance(e, dict) else None
                if not isinstance(name, str) or not name:
                    raise ValueError(f"reference {rid!r}: every 'expects' entry needs a "
                                     f"non-empty str 'name', got {e!r}")
                if name in names:
                    raise ValueError(f"reference {rid!r}: duplicate expectation name "
                                     f"{name!r}")
                names.append(name)
                _check_expect(f"reference {rid!r}: expects[{name!r}]", e, cands, classes)
    if len(set(ids)) != len(ids):
        raise ValueError(f"duplicate panel reference ids: {ids!r}")
    overlap = sorted(str(r) for r in set(ids) & set(cands))
    if overlap:
        raise ValueError("panel references must never be candidates (same-body "
                         f"cross-contamination): {overlap}")
    for uid in ids + cands:
        if uid not in grids:
            raise KeyError(f"no grid for unit {uid!r}")
        for name, m in (("spacings", spacings), ("rights", rights)):
            if isinstance(m, dict) and uid not in m:
                raise KeyError(f"{name} has no entry for unit {uid!r}")
    return classes


def _run_cell(units, spacings, ref_id, extent_m, support_m, decision_metrics,
              rights, compare_kw):
    """One matched cell; any exception becomes an ERROR record (never raises)."""
    try:
        c = _mb.matched_cell(units, spacings, ref_id, extent_m, support_m,
                             decision_metrics=decision_metrics, rights=rights,
                             **compare_kw)
    except Exception as exc:  # noqa: BLE001 -- a bad cell must not crash the panel
        return {"support_m": float(support_m), "result_state": ERROR_STATE,
                "recommended_unit": None, "pareto_layer1": [],
                "pareto_layers": [], "dominance_matrix": {},
                "compared_units": sorted(str(u) for u in units), "provenance": {},
                "error": f"{type(exc).__name__}: {exc}"}
    prov = c.get("provenance") or {}
    rec = {"support_m": float(support_m), "result_state": c.get("result_state"),
           "recommended_unit": c.get("recommended_unit"),
           "pareto_layer1": list(c.get("pareto_layer1") or []),
           "pareto_layers": [list(layer) for layer in (c.get("pareto_layers") or [])],
           "dominance_matrix": dict(c.get("dominance_matrix") or {}),
           "compared_units": sorted(str(u) for u in prov),
           "provenance": prov, "error": None}
    for k in _OPTIONAL_CELL_KEYS:
        if k in c:
            rec[k] = c[k]
    return rec


def _run_adequacy(units, spacings, ref_id, extent_m, support_m, rights):
    """Absolute-adequacy summary for one reference; never raises."""
    try:
        a = _adequacy.adequacy_assessment(units, spacings, ref_id, extent_m,
                                          support_m, rights=rights)
    except Exception as exc:  # noqa: BLE001
        return {"support_m": float(support_m), "established": False,
                "adequate_candidates": [], "any_adequate": False,
                "note": _adequacy.NOT_ESTABLISHED_NOTE,
                "error": f"{type(exc).__name__}: {exc}"}
    return {"support_m": float(support_m), "established": bool(a["established"]),
            "adequate_candidates": list(a["adequate_candidates"]),
            "any_adequate": bool(a["any_adequate"]), "note": a["note"], "error": None}


def _pair_key(a, b):
    """``dominance_matrix`` key for a pair: the two ids sorted, joined by '|'
    (exactly as :func:`frontier.dominance_matrix` builds it)."""
    i, j = sorted((a, b))
    return f"{i}|{j}"


def _class_cell_satisfies(expect, cell, candidate_classes):
    """One non-ERROR cell vs a class expectation (baseline Pareto relations only)."""
    def members(cls):
        return [u for u, c in candidate_classes.items() if c == cls]

    if expect["type"] == "class_in_layer1":
        layer1 = cell.get("pareto_layer1") or []
        return any(u in layer1 for u in members(expect["class"]))
    dom = cell.get("dominance_matrix") or {}
    losers = members(expect["loser_class"])
    if not losers:                  # never vacuously true (validation forbids it)
        return False
    return any(all(dom.get(_pair_key(w, loser)) == w for loser in losers)
               for w in members(expect["winner_class"]))


def _cell_satisfies(expect, cell, candidate_classes=None):
    """Whether one cell satisfies a predeclared expectation (ERROR -> False)."""
    if cell.get("result_state") == ERROR_STATE:
        return False
    if isinstance(expect, dict) and expect.get("type") in CLASS_EXPECT_TYPES:
        return _class_cell_satisfies(expect, cell, candidate_classes)
    unit = expect["unit"]
    sole = cell.get("result_state") == RECOMMEND and cell.get("recommended_unit") == unit
    kind = expect["type"]
    if kind == "recommends":
        return bool(sole)
    if kind == "non_dominated":
        return unit in (cell.get("pareto_layer1") or [])
    if kind == "not_sole":
        return not sole
    raise ValueError(f"unknown expectation type {kind!r}")


def evaluate_expectation(expect, cells, candidate_classes=None):
    """Evaluate a PREDECLARED expectation over a reference's per-support cells.

    ``expect`` is None or {"type": "recommends"|"non_dominated"|"not_sole",
    "unit": candidate_id}. Per support: "recommends" is satisfied iff the cell is a
    single RECOMMEND_FOLLOW_UP of ``unit``; "non_dominated" iff ``unit`` is in the
    first Pareto layer; "not_sole" iff the cell is NOT a single
    RECOMMEND_FOLLOW_UP of ``unit``. ERROR cells are never satisfied and are
    listed in ``error_supports``. ``outcome`` is "holds" (all supports satisfied),
    "fails" (none), "mixed" (some), or "not_predeclared" (no expectation -- nothing
    is inferred after the fact). The expectation itself is copied, never edited.

    Class expectations need ``candidate_classes`` ({candidate_id: class}; a
    ValueError otherwise, or if a named class has no candidate):
    {"type": "class_in_layer1", "class": C} is satisfied iff some candidate of C is
    in ``pareto_layer1``; {"type": "class_dominates", "winner_class": W,
    "loser_class": L} iff SOME candidate w of W has ``dominance_matrix[pair(w, l)]
    == w`` for EVERY candidate l of L (a missing pair counts as not dominated).
    Both read the baseline Pareto relations, whatever the cell's result_state
    (except ERROR); the outcome aggregation is the same as for the unit types.
    """
    errors = [float(c["support_m"]) for c in cells
              if c.get("result_state") == ERROR_STATE]
    if expect is None:
        return {"declared": None, "outcome": "not_predeclared",
                "satisfied_fraction": None, "per_support": [],
                "error_supports": errors}
    if isinstance(expect, dict) and expect.get("type") in CLASS_EXPECT_TYPES:
        _check_class_expect("evaluate_expectation", expect, candidate_classes)
    per = [{"support_m": float(c["support_m"]),
            "satisfied": bool(_cell_satisfies(expect, c, candidate_classes))}
           for c in cells]
    n_sat = sum(1 for p in per if p["satisfied"])
    frac = float(n_sat / len(per)) if per else 0.0
    if per and n_sat == len(per):
        outcome = "holds"
    elif n_sat == 0:
        outcome = "fails"
    else:
        outcome = "mixed"
    return {"declared": copy.deepcopy(expect), "outcome": outcome,
            "satisfied_fraction": frac, "per_support": per,
            "error_supports": errors}


def _empty_counts():
    return {o: 0 for o in OUTCOMES}


def _mode_unit(counts):
    """Most-recommended unit; ties broken alphabetically; None if no recommendation."""
    best = [u for u, n in counts.items() if n > 0]
    if not best:
        return None
    return sorted(best, key=lambda u: (-counts[u], str(u)))[0]


def _summarise(records, candidate_ids, n_supports):
    """Per-class outcome counts + recommendation modes, and the specificity verdict."""
    classes = {}
    for r in records:
        classes.setdefault(r["class"], []).append(r)
    by_class = {}
    for cls in sorted(classes):
        refs = classes[cls]
        outcomes = _empty_counts()
        by_status = {s: _empty_counts() for s in STATUSES}
        rec_counts = {str(c): 0 for c in candidate_ids}
        n_err = 0
        for r in refs:
            o = r["expectation"]["outcome"]
            outcomes[o] += 1
            by_status[r["status"]][o] += 1
            for cell in r["cells"]:
                if cell["result_state"] == ERROR_STATE:
                    n_err += 1
                u = cell.get("recommended_unit")
                if cell["result_state"] == RECOMMEND and u is not None:
                    rec_counts[str(u)] = rec_counts.get(str(u), 0) + 1
        n_cells = len(refs) * n_supports
        by_class[cls] = {
            "n_refs": len(refs),
            "ref_ids": [r["id"] for r in refs],
            "n_cells": n_cells,
            "n_error_cells": n_err,
            "outcomes": outcomes,
            "outcomes_by_status": by_status,
            "most_recommended_unit": _mode_unit(rec_counts),
            "recommended_fraction_by_unit": {
                u: (float(n / n_cells) if n_cells else 0.0)
                for u, n in sorted(rec_counts.items())},
        }

    tops = {cls: v["most_recommended_unit"] for cls, v in by_class.items()}
    n_classes = len(by_class)
    any_top = any(t is not None for t in tops.values())
    evaluable = bool(n_classes >= 2 and any_top)
    top_set = set(tops.values())
    same_top = bool(evaluable and len(top_set) == 1 and None not in top_set)
    if n_classes < 2:
        verdict = "not_evaluable"
        explanation = (
            f"Specificity needs at least one reference in each of at least two "
            f"reference classes; this panel has {n_classes} class(es), so it cannot "
            f"show whether the recommendation is particular to a terrain class.")
    elif not any_top:
        verdict = "not_evaluable"
        explanation = (
            "No reference in any class produced a RECOMMEND_FOLLOW_UP, so there is "
            "no recommended relationship whose specificity could be assessed.")
    elif same_top:
        unit = next(iter(top_set))
        verdict = "non_specific"
        explanation = (
            f"The same candidate ({unit}) is the most-recommended unit in every "
            f"reference class ({', '.join(sorted(by_class))}). The result is "
            f"NON-SPECIFIC: it most likely reflects {unit} being generically closest "
            f"within this candidate shortlist rather than an analog relationship "
            f"particular to any terrain class, and must not be presented as an "
            f"analog relationship.")
    else:
        parts = ", ".join(f"{cls} -> {tops[cls] if tops[cls] is not None else 'none'}"
                          for cls in sorted(tops))
        verdict = "specific"
        explanation = (
            f"The most-recommended candidate differs across reference classes "
            f"({parts}). The recommendation pattern is class-specific at this "
            f"footprint and these supports -- a necessary, not sufficient, condition "
            f"for an analog relationship; it is not proof of one.")
    specificity = {"evaluable": evaluable, "same_top_unit_across_classes": same_top,
                   "top_unit_by_class": tops, "verdict": verdict,
                   "explanation": explanation}

    status_counts = {s: sum(1 for r in records if r["status"] == s) for s in STATUSES}
    confirmatory_outcomes = _empty_counts()
    for r in records:
        if r["status"] == "confirmatory":
            confirmatory_outcomes[r["expectation"]["outcome"]] += 1
    return {
        "n_references": len(records),
        "n_supports": int(n_supports),
        "n_comparisons": len(records) * int(n_supports),
        "status_counts": status_counts,
        "confirmatory_outcomes": confirmatory_outcomes,
        "classes": by_class,
        "specificity": specificity,
    }


def run_reference_panel(grids, spacings, panel, candidate_ids, extent_m, supports,
                        decision_metrics="core", rights=None, adequacy=True,
                        adequacy_support_m=None, candidate_classes=None, **compare_kw):
    """Run a confirmation + specificity reference panel at a matched footprint.

    ``grids``: {uid: 2-D elevation grid} holding every panel reference and every
    candidate. ``spacings``: scalar source spacing (m) or {uid: m}. ``panel``: list
    of {"id", "class", "status": "exploratory"|"confirmatory", "expect": None or
    {"type": "recommends"|"non_dominated"|"not_sole", "unit": candidate_id}}.
    ``candidate_ids``: the shared candidate pool (must not contain panel ids).
    ``supports``: analysis supports (m); ``extent_m``: common matched footprint.

    Optional class hypotheses: ``candidate_classes`` ({candidate_id: class_name},
    one class for EVERY candidate) enables the ``class_in_layer1`` /
    ``class_dominates`` expectation types (see :func:`evaluate_expectation`), and a
    panel entry may add ``"expects": [{"name": str, ...expectation...}, ...]`` --
    several NAMED expectations (unique names per reference), reported under the
    reference's ``expectations``. Neither changes ``expect`` / ``expectation``,
    ``counts_as_confirmation`` or the summary, which refer to ``expect`` only.

    For each reference the compared set is {reference} + candidates ONLY; one
    :func:`matched_benchmark.matched_cell` runs per support (an exception becomes a
    ``result_state == "ERROR"`` cell carrying the message). When ``adequacy`` is
    true, absolute adequacy is calibrated at ``adequacy_support_m`` (default: the
    largest support). The predeclared expectation is then evaluated per support
    (:func:`evaluate_expectation`). ``rights`` and ``**compare_kw`` pass through to
    the engine unchanged.

    Returns a JSON-serialisable, deterministic dict::

        {"extent_m", "supports_m", "decision_metrics", "candidates",
         ["candidate_classes": {cand: class}  -- only when given],
         "references": [{"id", "class", "status", "counts_as_confirmation",
                         "compared_units", "cells": [...], "adequacy",
                         "expectation": {"declared", "outcome",
                                         "satisfied_fraction", "per_support",
                                         "error_supports"},
                         ["expectations": {name: <same shape>} -- only with
                          "expects"]}, ...],
         "summary": {"n_references", "n_supports", "n_comparisons",
                     "status_counts", "confirmatory_outcomes",
                     "classes": {cls: {...}}, "specificity": {...}},
         "note": str}

    Every cell also carries the baseline ``pareto_layers`` and ``dominance_matrix``
    (empty for an ERROR cell). Malformed predeclarations raise ``ValueError`` /
    ``KeyError`` BEFORE anything runs. The input ``panel`` is never mutated.
    """
    supports = [float(s) for s in supports]
    classes = _validate(grids, spacings, panel, candidate_ids, supports, rights,
                        candidate_classes)
    cands = list(candidate_ids)
    ade_sup = float(adequacy_support_m) if adequacy_support_m is not None else max(supports)

    records = []
    for entry in panel:
        rid = entry["id"]
        keys = [rid] + cands               # the reference + candidates ONLY
        units = {k: grids[k] for k in keys}
        sp = _sub_map(spacings, keys)
        rt = _sub_map(rights, keys)
        cells = [_run_cell(units, sp, rid, extent_m, s, decision_metrics, rt, compare_kw)
                 for s in supports]
        ade = _run_adequacy(units, sp, rid, extent_m, ade_sup, rt) if adequacy else None
        expect = copy.deepcopy(entry.get("expect"))
        status = entry["status"]
        record = {
            "id": rid,
            "class": entry["class"],
            "status": status,
            "counts_as_confirmation": bool(status == "confirmatory" and expect is not None),
            "compared_units": [str(k) for k in keys],
            "cells": cells,
            "adequacy": ade,
            "expectation": evaluate_expectation(expect, cells, classes),
        }
        if entry.get("expects") is not None:
            record["expectations"] = {
                e["name"]: evaluate_expectation(copy.deepcopy(e), cells, classes)
                for e in entry["expects"]}
        records.append(record)

    out = {
        "extent_m": float(extent_m),
        "supports_m": supports,
        "decision_metrics": decision_metrics,
        "candidates": [str(c) for c in cands],
    }
    if classes is not None:
        out["candidate_classes"] = dict(classes)
    out.update({
        "references": records,
        "summary": _summarise(records, cands, len(supports)),
        "note": PANEL_NOTE,
    })
    return out
