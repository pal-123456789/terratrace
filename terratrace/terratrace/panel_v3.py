"""Protocol v3 REFERENCE PANEL -- a direct test of the smoothness / shortlist explanation.

WHY THIS EXISTS. Protocol v2 (docs/RESULTS-v2.md) withdrew the Craters-of-the-Moon
analog claim. Its leading explanation -- at km scale Martian terrain is smoother than
every Earth tile, and the nearest candidate is simply the smoothest member of a weak
shortlist -- was consistent with v2 but never tested directly. Protocol v3
(docs/BENCHMARK-PROTOCOL-v3-PROPOSAL.md) tests it by adding SMOOTH NON-VOLCANIC Earth
controls next to the basaltic candidates and fresh Mars references, and by asking two
class-level questions of the engine's baseline Pareto relations:

  * S (smoothness / shortlist) -- is a ``smooth_control`` candidate non-dominated
    (Pareto layer 1) for Martian volcanic plains?
  * V (volcanic specificity)   -- does some ``basaltic`` candidate Pareto-dominate
    EVERY smooth control for volcanic plains, but not for highlands?

v2 also taught a protocol lesson: its H3 rule fired on STABILISATION (INDETERMINATE
-> RECOMMEND of the same nearest unit under resolution matching), not on a reversal.
:func:`classify_resolution_change` separates the two, and rule R reads only reversals.

WHAT IS REUSED. Everything except the v3 rules is the v2 machinery in
:mod:`matched_real`, called rather than copied: the rasterio seam
(:func:`matched_real.load_panel_grids`), the support plan and floor demotion, the
per-cell comparability labels and regime audit, the primary-reference block
(adversarial stress test), the sha256 of frozen inputs, bundle writing and the
ASCII-safe printing. The v2 runner itself (``matched_real.run_panel_from_grids``)
is a frozen, already-run experiment and is not touched by this module.

Scope / claim firewall (inherited, unchanged): map-scale terrain-MORPHOLOGY screening
only -- not a traversability, geologic-equivalence, site-access, or mission-readiness
claim. S and V are statements about class-level Pareto relations of morphology
descriptors, not about geological process.
"""
from __future__ import annotations

from . import gaps
from . import matched_real as mr

__all__ = [
    "classify_resolution_change",
    "evaluate_v3_hypotheses",
    "run_panel_v3_from_grids",
    "run_real_panel_v3",
    "CHANGE_CLASSES",
    "RULES_V3",
    "LIMITATIONS_V3",
    "EXPERIMENT_V3",
]

EXPERIMENT_V3 = "matched_footprint_panel_v3"
_BUNDLE_NAME = "matched_panel_v3_real.json"
_DEFAULT_OUT = "artifacts/mf_panel_v3"

CHANGE_CLASSES = ("unchanged", "stabilised", "destabilised", "reversed",
                  "membership_changed", "error")

# Which references the rules read, and their thresholds.
_PLAINS, _HIGHLAND = "volcanic_plains", "highland"
_N_PLAINS, _N_HIGHLAND = 3, 2
_MIN_PLAINS_HOLDS = 2          # S and V: >= 2 of the 3 confirmatory plains references
_MIN_HIGHLAND_NOT_HOLDS = 1    # V: >= 1 of the 2 confirmatory highland references
_SMOOTH, _BASALTIC = "smooth_control", "basaltic"
# The named expectations the rules read, exactly as the protocol declares them; a
# missing or differently-declared one means the rule does not apply (inconclusive).
_DECLARED = {"S": {"type": "class_in_layer1", "class": _SMOOTH},
             "V": {"type": "class_dominates", "winner_class": _BASALTIC,
                   "loser_class": _SMOOTH}}

RULES_V3 = {
    "S": ("S — Smoothness / shortlist. The nearest Earth candidate tracks km-scale "
          "smoothness, not volcanic origin. Supported if ≥ 2 of the 3 confirmatory "
          "volcanic_plains references have expectation S (class_in_layer1: some "
          "smooth_control candidate is in the baseline Pareto layer 1) with outcome holds "
          "(satisfied at every honest support). Not supported if ≤ 1. Inconclusive if the "
          "panel does not have exactly 3 confirmatory volcanic_plains references, or any of "
          "their honest cells is an ERROR."),
    "V": ("V — Volcanic specificity. Supported if ≥ 2 of the 3 confirmatory "
          "volcanic_plains references have expectation V (class_dominates: some basaltic "
          "candidate Pareto-dominates every smooth_control candidate) with outcome holds, "
          "and ≥ 1 of the 2 confirmatory highland references has expectation V with an "
          "outcome other than holds. Not supported otherwise. Inconclusive if the panel "
          "does not have exactly 3 confirmatory volcanic_plains and 2 confirmatory highland "
          "references, or any of their honest cells is an ERROR."),
    "R": ("R — Resolution robustness. Every honest cell of every confirmatory reference "
          "is classified raw vs resolution-matched (resolution.match_effective_resolution) "
          "as unchanged, stabilised, destabilised, reversed, membership_changed or error "
          "(panel_v3.classify_resolution_change). Not supported if any cell is reversed "
          "(the nearest candidate changed). Supported otherwise. Inconclusive if the "
          "resolution control was not run or any classified cell is an error."),
}
EVIDENCE_RULE_V3 = (
    "Evidence: honest supports only (at or above the support floor), core lens, "
    "confirmatory references only; exploratory and calibration references are reported "
    "but never counted. A predeclared S or V expectation that is missing or declared "
    "differently makes its rule inconclusive. Comparability gate: if any honest-support "
    "cell of a confirmatory reference (raw or resolution-matched) is outside the honest "
    "regime (a +low-power suffix is allowed), S, V and R are inconclusive and each "
    "rule's own result is kept as rule_verdict.")
_HYP_NAMES = {"S": "smoothness/shortlist", "V": "volcanic specificity",
              "R": "resolution robustness"}
_ROBUSTNESS_LABEL = ("robustness info -- S and V re-evaluated on the resolution-matched "
                     "panel; not a hypothesis, never evidence")
_ADEQUACY_LABEL = "reported -- no predeclared direction; never evidence for S, V or R"

LIMITATIONS_V3 = (
    "Not independent replications: all Mars references share one source (MOLA) and all "
    "Earth candidates share one (COP30); references × honest supports are multiple "
    "comparisons, reported as such, with no correction applied.",
    "COP30 is a surface model (DSM), not bare earth: it includes vegetation and "
    "buildings. The chosen areas are sparsely built and vegetated; this is a stated "
    "limitation, not a correction.",
    "Representativeness: each window samples a small part of a named unit; coordinates "
    "are approximate named-feature centres, some taken from secondary sources.",
    "The 3× effective-resolution figure is a heuristic, not a measured MOLA transfer "
    "function; the resolution control equalises resolving power under that heuristic "
    "and adds no information.",
    "Candidate classes (basaltic / smooth_control / others) are assigned from the "
    "literature before the run. S and V test class-level Pareto relations of map-scale "
    "morphology descriptors; they read the baseline frontier, so they can hold in TIE or "
    "INDETERMINATE cells and are not recommendations.",
    "Morphology only: no traversability, geologic-equivalence, process, site-access, or "
    "mission claim.",
)


# --------------------------------------------------------------------------- #
# Resolution-change classifier (the v2 H3 lesson)                              #
# --------------------------------------------------------------------------- #
def classify_resolution_change(raw_cell, matched_cell):
    """Classify how ONE cell changed between the raw and the resolution-matched run.

    Pure and deterministic; reads ``result_state``, ``recommended_unit`` and
    ``pareto_layer1`` only. With X the raw nearest unit:

      * ``error``        -- either cell is missing or ERROR;
      * ``unchanged``    -- same result_state, same recommended_unit, same layer-1 set;
      * ``stabilised``   -- raw is not RECOMMEND_FOLLOW_UP, raw layer 1 == {X}, and the
        matched cell is RECOMMEND_FOLLOW_UP of X (the exact v2 situation:
        INDETERMINATE -> RECOMMEND of the same nearest unit);
      * ``destabilised`` -- raw is RECOMMEND_FOLLOW_UP of X, matched is not, and X is
        still in the matched layer 1;
      * ``reversed``     -- the nearest unit changed: raw RECOMMEND X and matched
        RECOMMEND Y != X; or raw RECOMMEND X and X not in the matched layer 1; or raw
        layer 1 == {X} and X not in the matched layer 1 (also when the matched cell has
        no layer 1 at all); or the two (non-empty) layer-1 sets are disjoint;
      * ``membership_changed`` -- anything else (typically the layer-1 sets overlap but
        differ, e.g. TIE {X, Y} -> RECOMMEND X).

    The checks run in that order, so a stabilisation is never read as a reversal.
    """
    from . import confirmation as cf
    if raw_cell is None or matched_cell is None:
        return "error"
    rs, ms = raw_cell.get("result_state"), matched_cell.get("result_state")
    if cf.ERROR_STATE in (rs, ms):
        return "error"
    r1 = set(raw_cell.get("pareto_layer1") or [])
    m1 = set(matched_cell.get("pareto_layer1") or [])
    if (rs == ms and raw_cell.get("recommended_unit") == matched_cell.get("recommended_unit")
            and r1 == m1):
        return "unchanged"
    raw_rec, m_rec = rs == cf.RECOMMEND, ms == cf.RECOMMEND
    x_raw = raw_cell.get("recommended_unit") if raw_rec else None
    x_m = matched_cell.get("recommended_unit") if m_rec else None
    sole_raw = next(iter(r1)) if len(r1) == 1 else None
    if not raw_rec and sole_raw is not None and m_rec and x_m == sole_raw:
        return "stabilised"
    if raw_rec and not m_rec and x_raw in m1:
        return "destabilised"
    if ((raw_rec and m_rec and x_m != x_raw)
            or (raw_rec and x_raw not in m1)
            or (sole_raw is not None and sole_raw not in m1)
            or (r1 and m1 and r1.isdisjoint(m1))):
        return "reversed"
    return "membership_changed"


def _change_rows(raw_panel, matched_panel, support_class):
    """Raw vs resolution-matched classification for every (reference, support) of one
    panel run. A row is ``counted`` iff it is an honest cell of a confirmatory reference."""
    mc = mr._cells(matched_panel)
    rows = []
    for r in (raw_panel or {}).get("references", []):
        for c in r["cells"]:
            s = float(c["support_m"])
            m = mc.get((r["id"], s))
            rows.append({
                "reference": r["id"], "class": r["class"], "status": r["status"],
                "support_m": s, "support_class": support_class,
                "counted": bool(support_class == "honest" and r["status"] == "confirmatory"),
                "raw_state": c["result_state"], "raw_layer1": list(c.get("pareto_layer1") or []),
                "raw_recommendation": mr._sole(c),
                "matched_state": None if m is None else m["result_state"],
                "matched_layer1": None if m is None else list(m.get("pareto_layer1") or []),
                "matched_recommendation": mr._sole(m),
                "change": classify_resolution_change(c, m)})
    return rows


def _change_counts(rows):
    counts = {k: 0 for k in CHANGE_CLASSES}
    for row in rows:
        counts[row["change"]] += 1
    return counts


# --------------------------------------------------------------------------- #
# The v3 decision rules (S, V, R) + comparability gate                         #
# --------------------------------------------------------------------------- #
_NO_HONEST = "no honest support survived the support floor -- nothing to evaluate"


def _named(record, name):
    return (record.get("expectations") or {}).get(name)


def _outcome(record, name):
    e = _named(record, name)
    return "not_predeclared" if e is None else e["outcome"]


def _declared_ok(record, name):
    e = _named(record, name)
    decl = (e or {}).get("declared") or {}
    return all(decl.get(k) == v for k, v in _DECLARED[name].items())


def _named_fact(record, name, counted):
    """Compact per-support facts behind one reference's named-expectation outcome."""
    by_s = {float(c["support_m"]): c for c in record["cells"]}
    e = _named(record, name)
    fact = {"status": record["status"], "class": record["class"],
            "counts_as_confirmation": bool(counted)}
    if e is None:
        fact.update(declared=None, outcome="not_predeclared", per_support=[],
                    error_supports=[float(c["support_m"]) for c in record["cells"]
                                    if c["result_state"] == "ERROR"])
        return fact
    fact.update(declared=e["declared"], outcome=e["outcome"],
                per_support=[{"support_m": p["support_m"], "satisfied": p["satisfied"],
                              "result_state": by_s[p["support_m"]]["result_state"],
                              "pareto_layer1": list(by_s[p["support_m"]].get("pareto_layer1")
                                                    or [])}
                             for p in e["per_support"]],
                error_supports=list(e["error_supports"]))
    return fact


def _confirmatory(honest, cls):
    return [r for r in (honest or {}).get("references", [])
            if r["class"] == cls and r["status"] == "confirmatory"]


def _not_counted(honest, counted, name):
    ids = {r["id"] for r in counted}
    return {r["id"]: _named_fact(r, name, False)
            for r in (honest or {}).get("references", []) if r["id"] not in ids}


def _verdict(verdict, key, reason, evidence, counts):
    return {"verdict": verdict, "rule": RULES_V3[key], "reason": reason,
            "evidence": evidence, "counts": counts}


def _hypothesis_s(honest):
    """S: supported iff >= 2 of the 3 confirmatory volcanic_plains references hold S."""
    plains = _confirmatory(honest, _PLAINS)
    holds = [r["id"] for r in plains if _outcome(r, "S") == "holds"]
    wrong = [r["id"] for r in plains if not _declared_ok(r, "S")]
    errored = [r["id"] for r in plains if mr._has_error(r)]
    evidence = {r["id"]: _named_fact(r, "S", True) for r in plains}
    counts = {"confirmatory_plains_refs": len(plains), "holds": len(holds),
              "holds_ids": holds, "required_holds": _MIN_PLAINS_HOLDS,
              "frozen_n_plains": _N_PLAINS}
    if honest is None:
        out = _verdict("inconclusive", "S", _NO_HONEST, evidence, counts)
    elif len(plains) != _N_PLAINS:
        out = _verdict("inconclusive", "S",
                       f"{len(plains)} confirmatory {_PLAINS} reference(s); the rule is "
                       f"defined over exactly {_N_PLAINS}", evidence, counts)
    elif wrong:
        out = _verdict("inconclusive", "S",
                       f"expectation S is missing or not declared as class_in_layer1 "
                       f"{_SMOOTH} for {wrong}; the rule does not apply", evidence, counts)
    elif errored:
        out = _verdict("inconclusive", "S",
                       f"ERROR cell(s) at honest supports for {errored} -- the rule is not "
                       f"applied to failed comparisons", evidence, counts)
    elif len(holds) >= _MIN_PLAINS_HOLDS:
        out = _verdict("supported", "S",
                       f"{len(holds)} of {_N_PLAINS} confirmatory plains references hold S "
                       f"(>= {_MIN_PLAINS_HOLDS} required): {holds}", evidence, counts)
    else:
        out = _verdict("not_supported", "S",
                       f"{len(holds)} of {_N_PLAINS} confirmatory plains references hold S "
                       f"(<= {_MIN_PLAINS_HOLDS - 1})", evidence, counts)
    out["not_counted"] = _not_counted(honest, plains, "S")
    return out


def _hypothesis_v(honest):
    """V: supported iff >= 2 of 3 confirmatory plains hold V AND >= 1 of 2 confirmatory
    highland references do not; not supported otherwise."""
    plains, high = _confirmatory(honest, _PLAINS), _confirmatory(honest, _HIGHLAND)
    p_holds = [r["id"] for r in plains if _outcome(r, "V") == "holds"]
    h_not = [r["id"] for r in high if _outcome(r, "V") != "holds"]
    counted = plains + high
    wrong = [r["id"] for r in counted if not _declared_ok(r, "V")]
    errored = [r["id"] for r in counted if mr._has_error(r)]
    evidence = {r["id"]: _named_fact(r, "V", True) for r in counted}
    counts = {"confirmatory_plains_refs": len(plains),
              "confirmatory_highland_refs": len(high),
              "plains_holds": len(p_holds), "plains_holds_ids": p_holds,
              "highland_not_holds": len(h_not), "highland_not_holds_ids": h_not,
              "required_plains_holds": _MIN_PLAINS_HOLDS,
              "required_highland_not_holds": _MIN_HIGHLAND_NOT_HOLDS,
              "frozen_n_plains": _N_PLAINS, "frozen_n_highland": _N_HIGHLAND}
    if honest is None:
        out = _verdict("inconclusive", "V", _NO_HONEST, evidence, counts)
    elif (len(plains), len(high)) != (_N_PLAINS, _N_HIGHLAND):
        out = _verdict("inconclusive", "V",
                       f"{len(plains)} confirmatory {_PLAINS} and {len(high)} confirmatory "
                       f"{_HIGHLAND} reference(s); the rule is defined over exactly "
                       f"{_N_PLAINS} and {_N_HIGHLAND}", evidence, counts)
    elif wrong:
        out = _verdict("inconclusive", "V",
                       f"expectation V is missing or not declared as class_dominates "
                       f"{_BASALTIC} > {_SMOOTH} for {wrong}; the rule does not apply",
                       evidence, counts)
    elif errored:
        out = _verdict("inconclusive", "V",
                       f"ERROR cell(s) at honest supports for {errored} -- the rule is not "
                       f"applied to failed comparisons", evidence, counts)
    elif len(p_holds) >= _MIN_PLAINS_HOLDS and len(h_not) >= _MIN_HIGHLAND_NOT_HOLDS:
        out = _verdict("supported", "V",
                       f"{len(p_holds)} of {_N_PLAINS} confirmatory plains references hold V "
                       f"({p_holds}) and {len(h_not)} of {_N_HIGHLAND} highland references "
                       f"do not ({h_not})", evidence, counts)
    else:
        parts = []
        if len(p_holds) < _MIN_PLAINS_HOLDS:
            parts.append(f"only {len(p_holds)} of {_N_PLAINS} confirmatory plains references "
                         f"hold V (>= {_MIN_PLAINS_HOLDS} required)")
        if len(h_not) < _MIN_HIGHLAND_NOT_HOLDS:
            parts.append(f"V holds for every confirmatory highland reference -- the "
                         f"basaltic advantage is not specific to volcanic plains")
        out = _verdict("not_supported", "V", "; ".join(parts), evidence, counts)
    out["not_counted"] = _not_counted(honest, counted, "V")
    return out


def _hypothesis_r(raw_honest, matched_honest, rc_ran):
    """R: not supported iff any confirmatory honest cell is ``reversed`` under
    resolution matching; supported otherwise (ERROR precedence -> inconclusive)."""
    rows = _change_rows(raw_honest, matched_honest, "honest") if rc_ran else []
    counted = [r for r in rows if r["counted"]]
    counts = _change_counts(counted)
    rev = [f"{r['reference']}@{r['support_m']:g} m" for r in counted
           if r["change"] == "reversed"]
    err = [f"{r['reference']}@{r['support_m']:g} m" for r in counted if r["change"] == "error"]
    evidence = {"rows": counted, "reversed_cells": rev}
    if not rc_ran:
        out = _verdict("inconclusive", "R", "the resolution control was not run "
                       "(resolution_control is false)", evidence, counts)
    elif raw_honest is None:
        out = _verdict("inconclusive", "R", _NO_HONEST, evidence, counts)
    elif not counted:
        out = _verdict("inconclusive", "R", "no confirmatory reference in the panel",
                       evidence, counts)
    elif err:
        out = _verdict("inconclusive", "R", f"ERROR cell(s) in the raw or resolution-matched "
                       f"run ({', '.join(err)}) -- the rule is not applied to failed "
                       f"comparisons", evidence, counts)
    elif rev:
        out = _verdict("not_supported", "R", f"the nearest candidate reverses under "
                       f"resolution matching at {', '.join(rev)}", evidence, counts)
    else:
        out = _verdict("supported", "R", f"no reversal among {len(counted)} confirmatory "
                       f"honest cell(s) ({counts['stabilised']} stabilised, "
                       f"{counts['destabilised']} destabilised, "
                       f"{counts['membership_changed']} membership_changed, "
                       f"{counts['unchanged']} unchanged)", evidence, counts)
    out["not_counted"] = {"rows": [r for r in rows if not r["counted"]],
                          "counts": _change_counts([r for r in rows if not r["counted"]])}
    return out


def _robustness_info(s_rule, v_rule, matched_honest, rc_ran):
    """S and V re-evaluated on the resolution-matched panel (rule verdicts, before the
    comparability gate). Reported only -- not a hypothesis."""
    if not rc_ran or matched_honest is None:
        return {"label": _ROBUSTNESS_LABEL, "evaluated": False,
                "reason": "the resolution control was not run"}
    ms, mv = _hypothesis_s(matched_honest), _hypothesis_v(matched_honest)
    info = {"label": _ROBUSTNESS_LABEL, "evaluated": True}
    for key, raw, m in (("S", s_rule, ms), ("V", v_rule, mv)):
        info[key] = {"raw_rule_verdict": raw["verdict"],
                     "resolution_matched_rule_verdict": m["verdict"],
                     "resolution_matched_reason": m["reason"],
                     "differs": bool(raw["verdict"] != m["verdict"])}
    info["any_differs"] = bool(info["S"]["differs"] or info["V"]["differs"])
    return info


def _apply_gate(hyp, violations):
    """Evidence only from honest-regime cells: any violation makes S, V and R
    inconclusive, keeping each rule's own result as ``rule_verdict``."""
    if not violations:
        return
    n = len(violations) if isinstance(violations, (list, tuple)) else None
    where = f"{n} honest-support cell(s)" if n is not None else "honest-support cell(s)"
    for key in ("S", "V", "R"):
        h = hyp[key]
        h["rule_verdict"], h["rule_reason"] = h["verdict"], h["reason"]
        h["verdict"] = "inconclusive"
        h["reason"] = (f"honest-regime violation in {where} of confirmatory references "
                       f"(see regime_violation) -- protocol v3 admits evidence only from "
                       f"honest-regime cells")


def _reading(hyp):
    s, v = hyp["S"], hyp["V"]
    # S and V cannot both be supported on engine cells. For ONE reference, S holds =>
    # at every honest support some smooth control is in Pareto layer 1, i.e. NO
    # candidate dominates it => no basaltic candidate can dominate EVERY smooth control
    # => V is satisfied at no support (V fails). Both rules read the same honest cells
    # and the same smooth_control class (the declaration check enforces it), S needs
    # >= 2 of the 3 plains references holding S and V needs >= 2 of the same 3 holding
    # V; 2 + 2 > 3, so one reference would hold both -- impossible. Only inconsistent
    # (fabricated) cells, whose layer 1 and dominance matrix disagree, could do it.
    if s["verdict"] == "supported" and v["verdict"] == "supported":
        return ("INCONSISTENT: S and V both supported -- impossible when Pareto layer 1 "
                "and the dominance matrix agree; inspect the cells")
    if s["verdict"] == "supported":
        return (f"smoothness/shortlist explanation supported: for "
                f"{s['counts']['holds']} of {_N_PLAINS} confirmatory volcanic-plains "
                f"references a smooth non-volcanic control is in Pareto layer 1 at every "
                f"honest support -- the nearest Earth candidates track km-scale smoothness, "
                f"not volcanic origin")
    if v["verdict"] == "supported":
        return (f"volcanic-specific signal supported: for {v['counts']['plains_holds']} of "
                f"{_N_PLAINS} confirmatory volcanic-plains references a basaltic candidate "
                f"Pareto-dominates every smooth control at every honest support, and for "
                f"{v['counts']['highland_not_holds']} of {_N_HIGHLAND} highland references "
                f"it does not")
    return (f"neither explanation supported by the pre-declared rules "
            f"(S {s['verdict']}, V {v['verdict']})")


def evaluate_v3_hypotheses(honest_panel, matched_honest_panel, comparability_violation,
                           rc_ran=None):
    """Apply the v3 decision rules S, V and R literally.

    ``honest_panel`` / ``matched_honest_panel`` are :func:`confirmation.run_reference_panel`
    outputs over the HONEST supports (raw and resolution-matched; either may be None).
    ``comparability_violation`` is the list of violating honest-support cells of
    confirmatory references (or any truthy flag); when present S, V and R become
    ``inconclusive`` with ``rule_verdict`` kept. ``rc_ran`` defaults to whether a
    matched panel was given. Evidence = honest supports of CONFIRMATORY references;
    exploratory / calibration references are reported under ``not_counted`` only.
    (The panel's own ``counts_as_confirmation`` refers to the single ``expect`` and is
    not read here.)

    Returns ``{"S", "V", "R", "robustness_info", "reading", "evidence_rule"}``; each
    verdict dict is ``{verdict, rule, reason, evidence, counts, not_counted
    [, rule_verdict, rule_reason]}``. Pure and deterministic.
    """
    if rc_ran is None:
        rc_ran = matched_honest_panel is not None
    hyp = {"S": _hypothesis_s(honest_panel), "V": _hypothesis_v(honest_panel),
           "R": _hypothesis_r(honest_panel, matched_honest_panel, bool(rc_ran))}
    robustness = _robustness_info(hyp["S"], hyp["V"], matched_honest_panel, bool(rc_ran))
    _apply_gate(hyp, comparability_violation)
    hyp["robustness_info"] = robustness
    hyp["reading"] = _reading(hyp)
    hyp["evidence_rule"] = EVIDENCE_RULE_V3
    return hyp


# --------------------------------------------------------------------------- #
# The runner                                                                   #
# --------------------------------------------------------------------------- #
def _confirmatory_view(panel_out):
    """The panel restricted to confirmatory references (for the comparability gate)."""
    if panel_out is None:
        return None
    return {"references": [r for r in panel_out.get("references", [])
                           if r["status"] == "confirmatory"]}


def _exploratory_view(panel_out):
    if panel_out is None:
        return None
    return {"references": [r for r in panel_out.get("references", [])
                           if r["status"] != "confirmatory"]}


def _adequacy_plan(cfg, honest, floor_m, warns):
    """Adequacy support as in v2: configured, else / below the floor -> the smallest
    honest support (substitution recorded and warned)."""
    ade_cfg = cfg.get("adequacy_support_m")
    ade_on = bool(cfg.get("adequacy", True)) and bool(honest)
    ade_sup, ade_sub = None, None
    if ade_on:
        if ade_cfg is None:
            ade_sup, ade_sub = honest[0], "not configured -> smallest honest support"
        elif float(ade_cfg) < floor_m:
            ade_sup = honest[0]
            ade_sub = (f"configured {float(ade_cfg):g} m is below the support floor "
                       f"{floor_m:g} m -> smallest honest support {honest[0]:g} m")
            warns.append(f"adequacy support substituted: {ade_sub}")
        else:
            ade_sup = float(ade_cfg)
    return {"run": ade_on, "configured_m": None if ade_cfg is None else float(ade_cfg),
            "support_m": ade_sup, "substituted": ade_sub is not None,
            "substitution": ade_sub}


def _adequacy_report(raw_honest, info):
    """Per reference: the adequacy band result and which layer-1 units fall inside it."""
    cells = mr._cells(raw_honest)
    per = {}
    for r in (raw_honest or {}).get("references", []):
        a = r.get("adequacy")
        cell = cells.get((r["id"], info.get("support_m")))
        layer1 = list((cell or {}).get("pareto_layer1") or [])
        if a is None:
            status, adequate = "not_run", None
        elif a.get("error") or not a.get("established"):
            status, adequate = "not_established", None
        else:
            adequate = list(a.get("adequate_candidates") or [])
            status = "some_adequate" if adequate else "none_adequate"
        per[r["id"]] = {"status_of_reference": r["status"], "class": r["class"],
                        "adequacy": status, "adequate_candidates": adequate,
                        "nearest_layer1": layer1,
                        "nearest_adequate": (None if adequate is None
                                             else [u for u in layer1 if u in adequate]),
                        "note": None if a is None else a.get("note")}
    return {"label": _ADEQUACY_LABEL, "support_m": info.get("support_m"),
            "per_reference": per}


def run_panel_v3_from_grids(grids, spacings, rights, cfg, out=None):
    """PURE (no rasterio) core of the v3 reference-panel experiment.

    Same footprint / support-floor / comparability / resolution-control / adequacy /
    adversarial machinery as v2 (:mod:`matched_real`, reused), plus candidate classes
    and the v3 rules:

      a. footprint -- :func:`comparability.common_matched_extent` (``extent_policy``
         ``min_available``: the largest window every used unit provides untruncated);
      b. supports  -- the support floor; configured honest supports below it are
         DEMOTED to diagnostic with a warning (:func:`matched_real._plan_supports`);
      c. raw panel -- :func:`confirmation.run_reference_panel` with
         ``candidate_classes``, run SEPARATELY on honest and diagnostic supports, with
         adequacy at ``adequacy_support_m`` (floor substitution as v2);
      d. comparability -- every cell labelled; the gate reads honest-support cells of
         CONFIRMATORY references (raw + resolution-matched);
      e. resolution control -- :func:`resolution.match_effective_resolution`, the same
         panel again, every cell classified by :func:`classify_resolution_change`;
      f. primary reference -- adversarial stress test at the smallest honest support
         (failures recorded, never raised);
      g. S, V, R -- :func:`evaluate_v3_hypotheses` (honest, confirmatory only);
      h. bundle -- ``out``/matched_panel_v3_real.json when ``out`` is set (sha256 of
         ``_config_path`` and ``protocol_path`` when given); i. a printed summary.

    Deterministic given the inputs; the bundle is JSON-serialisable.
    """
    import copy
    import numpy as np
    from . import comparability as cp, confirmation as cf, resolution as rz

    policy = cfg.get("extent_policy") or "min_available"
    if policy != "min_available":
        raise ValueError(f"extent_policy {policy!r} is not implemented (only "
                         f"'min_available')")
    panel = copy.deepcopy(list(cfg["panel"]))
    panel_ids, cands = mr._panel_ids(cfg)
    classes = cfg.get("candidate_classes")
    classes = None if classes is None else dict(classes)
    used = list(dict.fromkeys(panel_ids + cands))
    missing = [u for u in used if u not in grids]
    if missing:
        raise KeyError(f"no grid for unit(s) {missing}")
    g = {u: grids[u] for u in used}
    sp = {u: float(spacings[u]) for u in used}
    rt = {u: rights.get(u, "unknown") for u in used}
    res_factor = float(cfg.get("res_factor", 3.0))
    ck = {"min_valid": float(cfg.get("min_valid_fraction", 0.5)), "res_factor": res_factor}
    warns = []

    # (a) Footprint: the largest window EVERY used unit provides untruncated.
    footprint = dict(cp.common_matched_extent(g, sp, cfg.get("extent_m")), policy=policy)
    extent = footprint["extent_m"]

    # (b) Supports: floor over all units; sub-floor "honest" supports are demoted.
    floor = cp.support_floor_m(sp, res_factor)
    plan, plan_warns = mr._plan_supports(cfg, sp, res_factor, floor["floor_m"])
    warns += plan_warns
    honest, diagnostic = plan["honest_m"], plan["diagnostic_m"]
    if not honest:
        warns.append("no configured honest support is at or above the support floor -- "
                     "no hypothesis can be evaluated")
    adequacy_info = _adequacy_plan(cfg, honest, floor["floor_m"], warns)

    def _panel_run(gr, sups, adequacy):
        if not sups:
            return None
        res = cf.run_reference_panel(
            gr, sp, panel, cands, extent, sups, decision_metrics="core", rights=rt,
            adequacy=adequacy, adequacy_support_m=adequacy_info["support_m"] if adequacy else None,
            candidate_classes=classes, **ck)
        mr._attach_comparability(res)
        return res

    # (c) Raw panel: honest (evidence) and diagnostic (never evidence), separately.
    raw = {"honest": _panel_run(g, honest, adequacy_info["run"]),
           "diagnostic": _panel_run(g, diagnostic, False)}

    # (e) Resolution control + per-cell change classification.
    rc_ran = bool(cfg.get("resolution_control"))
    if rc_ran:
        gm, rep = rz.match_effective_resolution(g, sp, res_factor)
        matched = {"honest": _panel_run(gm, honest, False),
                   "diagnostic": _panel_run(gm, diagnostic, False)}
        rows_h = _change_rows(raw["honest"], matched["honest"], "honest")
        rows_d = _change_rows(raw["diagnostic"], matched["diagnostic"], "diagnostic")
        resolution_control = {
            "run": True, "target_fwhm_m": rep["target_fwhm_m"], "units": rep["units"],
            "classification": rows_h + rows_d,
            "counts_honest_confirmatory": _change_counts([r for r in rows_h if r["counted"]]),
            "counts_honest_not_counted": _change_counts([r for r in rows_h if not r["counted"]]),
            "counts_diagnostic": _change_counts(rows_d),
            "diagnostic_label": mr._DIAGNOSTIC_LABEL,
            "panel_matched": matched}
    else:
        matched = {"honest": None, "diagnostic": None}
        resolution_control = {"run": False, "reason": "resolution_control is false in the config"}

    # (d) Comparability gate: honest-support cells of CONFIRMATORY references.
    violations, low_power, unassessed = mr._regime_audit(
        [("raw", _confirmatory_view(raw["honest"])),
         ("resolution_matched", _confirmatory_view(matched["honest"]))])
    other_viol, _, _ = mr._regime_audit(
        [("raw", _exploratory_view(raw["honest"])),
         ("resolution_matched", _exploratory_view(matched["honest"]))])
    if other_viol:
        warns.append(f"{len(other_viol)} honest-support cell(s) of exploratory/calibration "
                     f"references are outside the honest regime (reported; they are never "
                     f"evidence, so the gate does not read them)")

    # (f) Primary reference: adversarial stress test (core lens; v2 helper).
    primary_id = cfg.get("primary_reference")
    primary = mr._primary_block(g, sp, rt, cands, primary_id, extent,
                                honest[0] if honest else None,
                                dict(cfg, decision_metrics=cfg.get("decision_metrics", ["core"])),
                                floor["floor_m"], ck)

    # (g) The v3 decision rules.
    hyp = evaluate_v3_hypotheses(raw["honest"], matched["honest"], violations, rc_ran=rc_ran)

    config_path = cfg.get("_config_path") or cfg.get("config_path")
    protocol_path = cfg.get("protocol_path")
    if not protocol_path:
        warns.append("protocol_path is not set in the config -- this bundle does not record "
                     "which frozen protocol was in effect")
    provenance = {
        "units": {uid: {"grid_shape": list(np.shape(g[uid])), "spacing_m": sp[uid],
                        "available_extent_m": footprint["available_m"][uid],
                        "effective_resolution_m": floor["effective_m"][uid],
                        "rights_status": rt[uid],
                        "role": "panel_reference" if uid in panel_ids else "candidate",
                        "candidate_class": (classes or {}).get(uid) if uid in cands else None}
                  for uid in used},
        "unused_units": sorted(str(u) for u in grids if u not in g),
        "res_factor": res_factor, "min_valid_fraction": ck["min_valid"],
        "decision_metrics": "core", "seed": int(cfg.get("seed", 0)),
    }
    bundle = {
        "experiment": cfg.get("experiment", EXPERIMENT_V3),
        "protocol": {"path": protocol_path, "sha256": mr._frozen_sha256(protocol_path)},
        "config": {"path": config_path, "sha256": mr._frozen_sha256(config_path)},
        "rules": dict(RULES_V3, evidence=EVIDENCE_RULE_V3,
                      change_classes=list(CHANGE_CLASSES)),
        "panel_ids": panel_ids, "candidates": cands,
        "candidate_classes": None if classes is None else {c: classes[c] for c in cands},
        "primary_reference": primary_id,
        "footprint": footprint,
        "support_floor": floor,
        "supports": plan,
        "warnings": warns,
        "adequacy": dict(adequacy_info, report=_adequacy_report(raw["honest"], adequacy_info)),
        "panel_raw": raw,
        "comparability": {
            "assess_cell": "comparability.assess_cell(tol=0.05, min_cells=10)",
            "regime_by_cell": {"honest": mr._regime_table(raw["honest"]),
                               "diagnostic": mr._regime_table(raw["diagnostic"])},
            "low_power_cells": low_power, "unassessed_cells": unassessed},
        "regime_violation": {
            "flag": bool(violations), "cells": violations,
            "scope": "honest-support cells of confirmatory references, raw and "
                     "resolution-matched",
            "not_gated_exploratory_cells": other_viol},
        "resolution_control": resolution_control,
        "primary": primary,
        "hypotheses": hyp,
        "limitations": list(LIMITATIONS_V3),
        "provenance": provenance,
        "scope_note": mr._HONEST_NOTE,
        "panel_note": cf.PANEL_NOTE,
        "prohibited_claims": gaps.prohibited_claims(),
    }
    path = mr._write_bundle(bundle, out, _BUNDLE_NAME) if out is not None else None
    _print_summary(bundle, path)
    return bundle


def _flag(record, name, support_m):
    """'S+' satisfied / 'S-' not / 'S?' not predeclared, for one cell."""
    e = _named(record, name)
    if e is None:
        return f"{name}?"
    sat = next((p["satisfied"] for p in e["per_support"] if p["support_m"] == support_m), None)
    return f"{name}{'+' if sat else '-'}"


def _print_summary(b, path=None):
    """Plain, honest one-screen summary of a v3 bundle (ASCII-only output)."""
    def p(line=""):
        print(mr._ascii(line).rstrip())

    p("=" * 78)
    p("TerraTrace matched-footprint benchmark v3 -- REFERENCE PANEL (S / V / R)")
    p("=" * 78)
    p(f"protocol: {b['protocol']['path'] or 'n/a'}   config: {b['config']['path'] or 'n/a'}")
    fp, fl, sup = b["footprint"], b["support_floor"], b["supports"]
    lim = fp["limiting_unit"]
    p(f"footprint: {fp['extent_m']:.0f} m common extent "
      f"({'REDUCED from' if fp['reduced'] else 'requested'} {mr._fmt_m(fp['requested_m'])} m; "
      f"limiting unit {lim} provides {fp['available_m'][lim]:.0f} m untruncated)")
    p(f"support floor: {fl['floor_m']:.0f} m (limiting {fl['limiting_unit']}; effective "
      f"resolution = {b['provenance']['res_factor']:g} x source spacing, a heuristic)")
    p(f"honest supports (evidence): {', '.join(f'{s:g}' for s in sup['honest_m']) or 'none'} m"
      f"   diagnostic (NEVER evidence): "
      f"{', '.join(f'{s:g}' for s in sup['diagnostic_m']) or 'none'} m")
    for w in b["warnings"]:
        p(f"WARNING: {w}")
    cls = b["candidate_classes"] or {}
    p("candidates: " + ", ".join(f"{c} [{cls.get(c, '?')}]" for c in b["candidates"]))

    honest = b["panel_raw"]["honest"]
    if honest:
        p("")
        p("HONEST cells, core lens -- state, baseline Pareto layer 1, S/V satisfied "
          "(+ yes, - no, ? not declared) [regime]:")
        rows = []
        for r in honest["references"]:
            rows.append([r["id"], f"{r['class']}/{r['status']}"] + [
                f"{c['result_state']} L1=[{','.join(c.get('pareto_layer1') or [])}] "
                f"{_flag(r, 'S', c['support_m'])} {_flag(r, 'V', c['support_m'])} "
                f"[{c['comparability']['regime']}]" for c in r["cells"]])
        head = ["reference", "class/status"] + [f"{s:g} m" for s in honest["supports_m"]]
        widths = [max(len(str(x[i])) for x in rows + [head]) + 2 for i in range(len(head))]
        p("  " + "".join(f"{h:<{w}}" for h, w in zip(head, widths)))
        for row in rows:
            p("  " + "".join(f"{x:<{w}}" for x, w in zip(row, widths)))
        p("")
        p("per-reference outcomes over HONEST supports (S = class_in_layer1 smooth_control; "
          "V = class_dominates basaltic > smooth_control):")
        counted = {_PLAINS, _HIGHLAND}
        w_id = max(len(r["id"]) for r in honest["references"]) + 2
        w_cs = max(len(f"{r['class']}/{r['status']}") for r in honest["references"]) + 2
        for r in honest["references"]:
            p(f"  {r['id']:<{w_id}}{r['class'] + '/' + r['status']:<{w_cs}}"
              f"S={_outcome(r, 'S'):<17}V={_outcome(r, 'V'):<17}counts_as_confirmation="
              f"{r['status'] == 'confirmatory' and r['class'] in counted}")
    ade = b["adequacy"]["report"]
    if ade["per_reference"]:
        p(f"adequacy @ {mr._fmt_m(ade['support_m'])} m ({ade['label']}): " + "; ".join(
            f"{rid}: {v['adequacy']}"
            + (f" {v['adequate_candidates']}" if v["adequate_candidates"] else "")
            for rid, v in ade["per_reference"].items()))

    rc = b["resolution_control"]
    p("")
    if rc["run"]:
        ch = rc["counts_honest_confirmatory"]
        p(f"resolution control (every unit low-passed to {rc['target_fwhm_m']:.0f} m FWHM) -- "
          f"confirmatory honest cells: " + ", ".join(f"{k}={ch[k]}" for k in CHANGE_CLASSES))
        for row in rc["classification"]:
            if row["counted"] and row["change"] != "unchanged":
                p(f"  {row['reference']}@{row['support_m']:g} m: {row['change']} "
                  f"({row['raw_state']} [{','.join(row['raw_layer1'])}] -> "
                  f"{row['matched_state']} [{','.join(row['matched_layer1'] or [])}])")
        cd = rc["counts_diagnostic"]
        p("  not counted -- exploratory/calibration honest cells: " + ", ".join(
            f"{k}={v}" for k, v in rc["counts_honest_not_counted"].items() if v)
          + "; diagnostic cells: " + ", ".join(f"{k}={v}" for k, v in cd.items() if v))
    else:
        p(f"resolution control: not run ({rc['reason']})")

    pr = b["primary"]
    if pr.get("evaluated"):
        st = pr.get("adversarial")
        if st is None:
            p(f"primary {pr['reference_id']} adversarial stress test: not run")
        elif st.get("error"):
            p(f"primary {pr['reference_id']} adversarial stress test: ERROR ({st['error']})")
        else:
            p(f"primary {pr['reference_id']} adversarial stress test @ {pr['support_m']:g} m "
              f"(exploratory trust bounds): {st['verdict']}, stable "
              f"{st['stable_fraction']:.2f} over {st['n_perturbations']} perturbations; "
              f"reversing: {', '.join(st['reversing_conditions']) or 'none'}")
    else:
        p(f"primary reference: not evaluated ({pr.get('reason')})")

    h = b["hypotheses"]
    p("")
    for k in ("S", "V", "R"):
        p(f"{k} {_HYP_NAMES[k]:<22}: {h[k]['verdict'].upper()} -- {h[k]['reason']}")
        if "rule_verdict" in h[k]:
            p(f"   rule outcome before the comparability gate: {h[k]['rule_verdict'].upper()} "
              f"-- {h[k]['rule_reason']}")
    ri = h["robustness_info"]
    if ri["evaluated"]:
        p("robustness info (not a hypothesis): resolution-matched rule verdicts "
          f"S={ri['S']['resolution_matched_rule_verdict']} "
          f"(raw {ri['S']['raw_rule_verdict']}), "
          f"V={ri['V']['resolution_matched_rule_verdict']} "
          f"(raw {ri['V']['raw_rule_verdict']}); differs: {ri['any_differs']}")
    else:
        p(f"robustness info: not evaluated ({ri['reason']})")
    p(f"READING: {h['reading']}")
    if b["regime_violation"]["flag"]:
        p(f"REGIME VIOLATION: {len(b['regime_violation']['cells'])} honest-support cell(s) of "
          f"confirmatory references outside the honest regime -- S, V and R are inconclusive")
    p("")
    p("LIMITATIONS (protocol v3):")
    for line in b["limitations"]:
        p(f"  - {line}")
    p(f"NOTE: {mr._HONEST_NOTE}")
    if path:
        p(f"[bundle] wrote {path}")


def run_real_panel_v3(cfg, out=_DEFAULT_OUT):
    """Front door for the REAL v3 panel: per-body metric grids for every unit via the
    v2 rasterio seam (:func:`matched_real.load_panel_grids`), then the pure core. Raises
    :class:`ImportError` (from the loader) when rasterio is unavailable, so the CLI can
    print an honest blocked message instead of a traceback."""
    grids, spacings, rights = mr.load_panel_grids(cfg)   # <-- the ONLY rasterio step
    return run_panel_v3_from_grids(grids, spacings, rights, cfg, out=out)
