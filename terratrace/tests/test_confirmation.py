"""Confirmatory, frozen tests for the CONFIRMATION + SPECIFICITY reference panel.

This is EMPIRICAL METHOD VALIDATION (that the panel evaluates predeclared
expectations and the specificity verdict correctly), NOT a scientific claim about
Mars or any Earth terrain. It plants KNOWN relationships on synthetic terrain.

GROUND TRUTH (fixed, first-principles). Three candidates with well-separated
roughness: ``X`` moderate (amplitude 10), ``Y`` very smooth (1), ``Z`` very rough
(60). Two ``volcanic_plains`` references are statistically like X (independent
seeds); one ``contrast`` reference is statistically like Z. So:

  * SPECIFIC scenario (candidates X, Y, Z): plains -> X, contrast -> Z. The plains
    expectation "recommends X" holds, the contrast expectation "not_sole X" holds,
    and the most-recommended unit differs across classes -> verdict "specific".
  * NON-SPECIFIC scenario A (weak shortlist: Z dropped): X is the least-bad
    candidate for the rough contrast reference too, so X wins in every class ->
    verdict "non_specific", contrast "not_sole X" fails -- and adequacy shows X is
    NOT within the contrast reference's own variability (best-of-a-bad-field).
  * NON-SPECIFIC scenario B (contrast ref is itself X-like): X wins everywhere.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network.
Deterministic seeds; the >= 6x roughness gaps make every outcome robust.
"""
import copy
import json

import numpy as np

from terratrace import confirmation as cf, synthetic, study

_N = 160
_DX = 30.0
_EXTENT_M = 4800.0        # 160 px matched footprint
_SUPPORTS = [90.0, 150.0]
_CANDS = ["X", "Y", "Z"]


def _grids():
    """Frozen synthetic scene: 3 candidates + 2 plains refs + 1 contrast ref."""
    shape = (_N, _N)
    return {
        "X": synthetic.rough_field(shape, amplitude=10.0, seed=3),
        "Y": synthetic.rough_field(shape, amplitude=1.0, seed=4),
        "Z": synthetic.rough_field(shape, amplitude=60.0, seed=5),
        "plains_a": synthetic.rough_field(shape, amplitude=10.0, seed=11),
        "plains_b": synthetic.rough_field(shape, amplitude=10.0, seed=12),
        "contrast": synthetic.rough_field(shape, amplitude=60.0, seed=21),
    }


def _panel():
    """Predeclared expectations, frozen BEFORE any result is seen.

    plains_a formed the hypothesis (exploratory); plains_b is the held-out
    confirmation; contrast tests specificity.
    """
    return [
        {"id": "plains_a", "class": "volcanic_plains", "status": "exploratory",
         "expect": {"type": "recommends", "unit": "X"}},
        {"id": "plains_b", "class": "volcanic_plains", "status": "confirmatory",
         "expect": {"type": "recommends", "unit": "X"}},
        {"id": "contrast", "class": "contrast", "status": "confirmatory",
         "expect": {"type": "not_sole", "unit": "X"}},
    ]


def _run(grids=None, panel=None, cands=_CANDS, **kw):
    return cf.run_reference_panel(grids if grids is not None else _grids(), _DX,
                                  panel if panel is not None else _panel(), cands,
                                  _EXTENT_M, _SUPPORTS, **kw)


def _refs(out):
    return {r["id"]: r for r in out["references"]}


def test_specific_scenario_expectations_hold_and_verdict_specific():
    out = _run()
    refs = _refs(out)
    for rid in ("plains_a", "plains_b", "contrast"):
        e = refs[rid]["expectation"]
        assert e["outcome"] == "holds", (rid, e, refs[rid]["cells"])
        assert e["satisfied_fraction"] == 1.0 and e["error_supports"] == [], (rid, e)
    for rid in ("plains_a", "plains_b"):
        for c in refs[rid]["cells"]:
            assert c["result_state"] == "RECOMMEND_FOLLOW_UP" and c["recommended_unit"] == "X", c
    for c in refs["contrast"]["cells"]:
        assert c["recommended_unit"] == "Z", c
    s = out["summary"]
    assert s["classes"]["volcanic_plains"]["most_recommended_unit"] == "X", s
    assert s["classes"]["contrast"]["most_recommended_unit"] == "Z", s
    assert s["classes"]["volcanic_plains"]["recommended_fraction_by_unit"]["X"] == 1.0, s
    sp = s["specificity"]
    assert sp["evaluable"] is True and sp["same_top_unit_across_classes"] is False, sp
    assert sp["verdict"] == "specific", sp
    assert sp["top_unit_by_class"] == {"contrast": "Z", "volcanic_plains": "X"}, sp
    # Bookkeeping: refs x supports comparisons; status counts.
    assert s["n_references"] == 3 and s["n_comparisons"] == 3 * len(_SUPPORTS), s
    assert s["status_counts"] == {"exploratory": 1, "confirmatory": 2}, s
    # Adequacy agrees with the ground truth: the recommended unit is within each
    # reference's own variability.
    assert refs["plains_b"]["adequacy"]["adequate_candidates"] == ["X"], refs["plains_b"]
    assert refs["contrast"]["adequacy"]["adequate_candidates"] == ["Z"], refs["contrast"]


def test_exploratory_reference_never_counted_as_confirmation():
    out = _run()
    s, refs = out["summary"], _refs(out)
    assert refs["plains_a"]["counts_as_confirmation"] is False
    assert refs["plains_b"]["counts_as_confirmation"] is True
    by = s["classes"]["volcanic_plains"]["outcomes_by_status"]
    assert by["exploratory"]["holds"] == 1 and by["confirmatory"]["holds"] == 1, by
    # Only the two confirmatory references enter the confirmatory tally.
    assert s["confirmatory_outcomes"]["holds"] == 2, s["confirmatory_outcomes"]
    assert sum(s["confirmatory_outcomes"].values()) == 2, s["confirmatory_outcomes"]


def test_non_specific_weak_shortlist_candidate_wins_everywhere():
    # Drop Z: X is merely the least-bad candidate for the rough contrast ref.
    out = _run(cands=["X", "Y"])
    refs = _refs(out)
    sp = out["summary"]["specificity"]
    assert sp["verdict"] == "non_specific", sp
    assert sp["same_top_unit_across_classes"] is True, sp
    assert sp["top_unit_by_class"] == {"contrast": "X", "volcanic_plains": "X"}, sp
    assert "NON-SPECIFIC" in sp["explanation"] and "X" in sp["explanation"], sp
    c = refs["contrast"]["expectation"]
    assert c["outcome"] == "fails" and c["satisfied_fraction"] == 0.0, c
    assert refs["plains_b"]["expectation"]["outcome"] == "holds", refs["plains_b"]
    # The "winner" for the contrast ref is outside its own variability: best of a
    # bad field, not an adequate analog.
    ade = refs["contrast"]["adequacy"]
    assert ade["established"] is True and "X" not in ade["adequate_candidates"], ade
    assert out["summary"]["confirmatory_outcomes"]["fails"] == 1, out["summary"]


def test_non_specific_when_contrast_reference_is_itself_x_like():
    g = _grids()
    g["contrast"] = synthetic.rough_field((_N, _N), amplitude=10.0, seed=21)
    out = _run(grids=g)
    sp = out["summary"]["specificity"]
    assert sp["verdict"] == "non_specific", sp
    assert _refs(out)["contrast"]["expectation"]["outcome"] == "fails"


def test_panel_references_never_compared_with_each_other():
    out = _run()
    panel_ids = {p["id"] for p in _panel()}
    for r in out["references"]:
        allowed = sorted([r["id"]] + _CANDS)
        assert sorted(r["compared_units"]) == allowed, r["compared_units"]
        others = panel_ids - {r["id"]}
        for c in r["cells"]:
            assert c["compared_units"] == allowed, (r["id"], c["compared_units"])
            assert sorted(c["provenance"]) == allowed, (r["id"], sorted(c["provenance"]))
            assert set(c["pareto_layer1"]) <= set(_CANDS), c["pareto_layer1"]
            assert not (set(c["pareto_layer1"]) & others), c["pareto_layer1"]
    # A candidate pool that contains a panel reference is rejected up front.
    try:
        _run(cands=["X", "Y", "plains_b"])
    except ValueError as exc:
        assert "cross-contamination" in str(exc), exc
    else:
        raise AssertionError("a panel reference was accepted as a candidate")


def test_adequacy_block_and_not_predeclared_outcome():
    panel = _panel() + [{"id": "contrast_open", "class": "contrast",
                         "status": "exploratory", "expect": None}]
    g = _grids()
    g["contrast_open"] = synthetic.rough_field((_N, _N), amplitude=60.0, seed=22)
    out = _run(grids=g, panel=panel)
    refs = _refs(out)
    for r in out["references"]:
        a = r["adequacy"]
        assert {"established", "adequate_candidates", "any_adequate", "note"} <= set(a), a
        assert a["support_m"] == max(_SUPPORTS), a         # default: largest support
    e = refs["contrast_open"]["expectation"]
    assert e["outcome"] == "not_predeclared" and e["declared"] is None, e
    assert e["satisfied_fraction"] is None, e
    assert refs["contrast_open"]["counts_as_confirmation"] is False
    assert out["summary"]["classes"]["contrast"]["outcomes"]["not_predeclared"] == 1
    # Explicit adequacy support is honoured; adequacy=False omits the block.
    out2 = _run(adequacy_support_m=90.0)
    assert all(r["adequacy"]["support_m"] == 90.0 for r in out2["references"])
    out3 = _run(adequacy=False)
    assert all(r["adequacy"] is None for r in out3["references"])


def test_evaluate_expectation_mixed_and_error_rules():
    cells = [
        {"support_m": 90.0, "result_state": "RECOMMEND_FOLLOW_UP",
         "recommended_unit": "X", "pareto_layer1": ["X"]},
        {"support_m": 150.0, "result_state": "TIE", "recommended_unit": None,
         "pareto_layer1": ["X", "Z"]},
        {"support_m": 300.0, "result_state": "ERROR", "recommended_unit": None,
         "pareto_layer1": []},
    ]
    rec = cf.evaluate_expectation({"type": "recommends", "unit": "X"}, cells)
    assert rec["outcome"] == "mixed" and abs(rec["satisfied_fraction"] - 1 / 3) < 1e-12, rec
    assert rec["error_supports"] == [300.0], rec
    nd = cf.evaluate_expectation({"type": "non_dominated", "unit": "X"}, cells)
    assert [p["satisfied"] for p in nd["per_support"]] == [True, True, False], nd
    ns = cf.evaluate_expectation({"type": "not_sole", "unit": "X"}, cells)
    # not_sole: the RECOMMEND of X fails it, the TIE satisfies it, ERROR never does.
    assert [p["satisfied"] for p in ns["per_support"]] == [False, True, False], ns
    assert cf.evaluate_expectation({"type": "not_sole", "unit": "Z"}, cells[:2])["outcome"] == "holds"
    assert cf.evaluate_expectation({"type": "recommends", "unit": "Z"}, cells)["outcome"] == "fails"


def test_degenerate_reference_does_not_crash_panel():
    g = _grids()
    g["tiny"] = np.zeros((2, 2))                         # too small: engine raises
    g["void"] = np.full((_N, _N), np.nan)                # all nodata: engine abstains
    panel = _panel() + [
        {"id": "tiny", "class": "volcanic_plains", "status": "confirmatory",
         "expect": {"type": "recommends", "unit": "X"}},
        {"id": "void", "class": "contrast", "status": "confirmatory",
         "expect": {"type": "not_sole", "unit": "X"}},
    ]
    out = _run(grids=g, panel=panel)
    refs = _refs(out)
    tiny = refs["tiny"]
    for c in tiny["cells"]:
        assert c["result_state"] == "ERROR" and c["error"], c
        assert c["recommended_unit"] is None and c["pareto_layer1"] == [], c
    assert tiny["expectation"]["outcome"] == "fails", tiny["expectation"]
    assert tiny["expectation"]["error_supports"] == _SUPPORTS, tiny["expectation"]
    assert tiny["adequacy"]["established"] is False, tiny["adequacy"]
    for c in refs["void"]["cells"]:
        assert c["result_state"] != "RECOMMEND_FOLLOW_UP", c
    # The rest of the panel still ran and still holds.
    for rid in ("plains_a", "plains_b", "contrast"):
        assert refs[rid]["expectation"]["outcome"] == "holds", refs[rid]["expectation"]
    assert out["summary"]["classes"]["volcanic_plains"]["n_error_cells"] == len(_SUPPORTS)
    assert out["summary"]["specificity"]["verdict"] == "specific", out["summary"]


def test_specificity_not_evaluable_with_one_class():
    panel = [p for p in _panel() if p["class"] == "volcanic_plains"]
    sp = _run(panel=panel)["summary"]["specificity"]
    assert sp["evaluable"] is False and sp["verdict"] == "not_evaluable", sp
    assert sp["same_top_unit_across_classes"] is False, sp


def test_malformed_predeclaration_rejected_before_running():
    bad_cases = [
        [{"id": "plains_a", "class": "volcanic_plains", "status": "maybe", "expect": None}],
        [{"id": "plains_a", "class": "volcanic_plains", "status": "exploratory",
          "expect": {"type": "resembles", "unit": "X"}}],
        [{"id": "plains_a", "class": "volcanic_plains", "status": "exploratory",
          "expect": {"type": "recommends", "unit": "W"}}],
    ]
    for panel in bad_cases:
        try:
            _run(panel=panel)
        except ValueError:
            continue
        raise AssertionError(f"malformed panel accepted: {panel!r}")


def test_json_serialisable_deterministic_and_panel_not_mutated():
    panel = _panel()
    frozen = copy.deepcopy(panel)
    a = _run(panel=panel)
    assert panel == frozen, "the predeclared panel must never be edited"
    for key in ("extent_m", "supports_m", "decision_metrics", "candidates",
                "references", "summary", "note"):
        assert key in a, key
    dumped = json.dumps(a, sort_keys=True, allow_nan=False)
    assert json.loads(dumped)["summary"]["specificity"]["verdict"] == "specific"
    b = _run(panel=copy.deepcopy(frozen))
    assert dumped == json.dumps(b, sort_keys=True, allow_nan=False)
    # The declared expectation is carried through verbatim.
    assert _refs(a)["contrast"]["expectation"]["declared"] == frozen[2]["expect"]


def test_default_study_hash_unchanged_by_this_module():
    # Gated: adding the panel must not perturb the default study package.
    h = study.run_study()["package_hash"]
    assert len(h) == 64 and all(ch in "0123456789abcdef" for ch in h), h
    assert study.run_study()["package_hash"] == h


# --------------------------------------------------------------------------- #
# CANDIDATE-CLASS hypotheses -- KNOWN Pareto relations on synthetic terrain.    #
#                                                                               #
# rough_family = {R1, R2} (amp 30), smooth_family = {S1 (amp 2), S2 (amp 1)}.   #
# rough_ref is R-like (amp 30), smooth_ref is S-like (amp 1.5). Against         #
# rough_ref every R is >= 10x closer than every S on slope/relief/ruggedness    #
# and no worse on connectivity, so EVERY R dominates EVERY S and layer 1 holds  #
# only R's (against smooth_ref: the mirror image, >= 50x). T is an EXACT copy   #
# of rough_ref: its distance vector is identically 0, so -- by construction,    #
# whatever the seeds -- nothing dominates T and T dominates every candidate     #
# that is not itself a copy. The tests read these relations off each cell's     #
# baseline frontier before relying on them.                                    #
# --------------------------------------------------------------------------- #
_CLS = {"R1": "rough_family", "R2": "rough_family",
        "S1": "smooth_family", "S2": "smooth_family"}
_CLS_CANDS = ["R1", "R2", "S1", "S2"]
_ROUGH, _SMOOTH = ("R1", "R2"), ("S1", "S2")


def _class_grids():
    """Frozen class scene: 4 classed candidates, 2 references, T = rough_ref twin."""
    def rf(amp, seed):
        return synthetic.rough_field((_N, _N), amplitude=amp, seed=seed)
    g = {"R1": rf(30.0, 41), "R2": rf(30.0, 42), "S1": rf(2.0, 43), "S2": rf(1.0, 44),
         "rough_ref": rf(30.0, 31), "smooth_ref": rf(1.5, 32)}
    g["T"] = g["rough_ref"].copy()
    return g


def _dom(winner, loser):
    return {"type": "class_dominates", "winner_class": winner, "loser_class": loser}


def _in_l1(cls):
    return {"type": "class_in_layer1", "class": cls}


def _winner(dom, a, b):
    """Dominance-matrix entry for a pair (key = the two ids sorted, '|'-joined)."""
    return dom["|".join(sorted((a, b)))]


def _class_panel():
    """Predeclared class hypotheses, frozen BEFORE any result is seen."""
    return [
        {"id": "rough_ref", "class": "rough_terrain", "status": "confirmatory",
         "expect": _dom("rough_family", "smooth_family"),
         "expects": [dict(_dom("rough_family", "smooth_family"), name="S"),
                     dict(_in_l1("rough_family"), name="V"),
                     dict(_in_l1("smooth_family"), name="smooth_in_layer1"),
                     dict(_dom("smooth_family", "rough_family"), name="reverse"),
                     {"name": "S1_not_sole", "type": "not_sole", "unit": "S1"}]},
        {"id": "smooth_ref", "class": "smooth_terrain", "status": "confirmatory",
         "expects": [dict(_dom("smooth_family", "rough_family"), name="S"),
                     dict(_in_l1("smooth_family"), name="V"),
                     dict(_in_l1("rough_family"), name="rough_in_layer1"),
                     dict(_dom("rough_family", "smooth_family"), name="reverse")]},
    ]


_CLASS_CACHE = {}


def _class_run():
    """The class panel, computed once (with the panel object it was given)."""
    if "out" not in _CLASS_CACHE:
        panel = _class_panel()
        _CLASS_CACHE["panel"] = panel
        _CLASS_CACHE["out"] = cf.run_reference_panel(
            _class_grids(), _DX, panel, _CLS_CANDS, _EXTENT_M, _SUPPORTS,
            candidate_classes=dict(_CLS))
    return copy.deepcopy(_CLASS_CACHE["out"])


def test_class_expectations_hold_and_fail_on_known_pareto_relations():
    out = _class_run()
    assert out["candidate_classes"] == _CLS, out["candidate_classes"]
    refs = _refs(out)
    # Ground truth first, straight off every cell's baseline frontier.
    for rid, near, far in (("rough_ref", _ROUGH, _SMOOTH), ("smooth_ref", _SMOOTH, _ROUGH)):
        for c in refs[rid]["cells"]:
            assert set(c["pareto_layer1"]) <= set(near), (rid, c["pareto_layer1"])
            assert all(_winner(c["dominance_matrix"], w, l) == w
                       for w in near for l in far), (rid, c["dominance_matrix"])
    want = {"rough_ref": {"S": "holds", "V": "holds", "smooth_in_layer1": "fails",
                          "reverse": "fails", "S1_not_sole": "holds"},
            "smooth_ref": {"S": "holds", "V": "holds", "rough_in_layer1": "fails",
                           "reverse": "fails"}}
    for rid, outcomes in want.items():
        got = refs[rid]["expectations"]
        assert {n: e["outcome"] for n, e in got.items()} == outcomes, (rid, got)
        for name, outcome in outcomes.items():
            e = got[name]
            assert e["error_supports"] == [], e
            assert e["satisfied_fraction"] == (1.0 if outcome == "holds" else 0.0), e
            assert [p["support_m"] for p in e["per_support"]] == _SUPPORTS, e
    # A class type also works as the single `expect` and enters the summary as usual.
    assert refs["rough_ref"]["expectation"]["outcome"] == "holds"
    assert refs["rough_ref"]["counts_as_confirmation"] is True
    s = out["summary"]
    assert s["classes"]["rough_terrain"]["outcomes"]["holds"] == 1, s
    json.dumps(out, sort_keys=True, allow_nan=False)


def test_class_dominates_fails_when_a_loser_class_member_is_non_dominated():
    # Put T (rough_ref's exact twin, zero distance vector) in the LOSER class. Every
    # R still beats S1 and S2, but no R can beat T: one non-dominated loser breaks
    # "some winner dominates EVERY loser". Conversely T alone makes smooth_family
    # dominate every rough member (EXISTS one winner), and puts it in layer 1.
    classes = dict(_CLS, T="smooth_family")
    panel = [{"id": "rough_ref", "class": "rough_terrain", "status": "confirmatory",
              "expects": [dict(_dom("rough_family", "smooth_family"), name="S"),
                          dict(_in_l1("smooth_family"), name="smooth_in_layer1"),
                          dict(_dom("smooth_family", "rough_family"), name="reverse")]}]
    out = cf.run_reference_panel(_class_grids(), _DX, panel, _CLS_CANDS + ["T"],
                                 _EXTENT_M, _SUPPORTS, candidate_classes=classes,
                                 adequacy=False)
    r = out["references"][0]
    for c in r["cells"]:
        dom = c["dominance_matrix"]
        assert "T" in c["pareto_layer1"], c["pareto_layer1"]
        for w in _ROUGH:
            assert _winner(dom, w, "T") == "T", dom
            assert all(_winner(dom, w, s) == w for s in _SMOOTH), dom
    e = r["expectations"]
    assert e["S"]["outcome"] == "fails" and e["S"]["satisfied_fraction"] == 0.0, e["S"]
    assert e["smooth_in_layer1"]["outcome"] == "holds", e["smooth_in_layer1"]
    assert e["reverse"]["outcome"] == "holds", e["reverse"]
    assert out["candidate_classes"] == classes, out["candidate_classes"]


def test_class_rules_exist_forall_and_ignore_recommendation_state():
    full = {"R1|R2": "R2", "R1|S1": "R1", "R1|S2": "R1",
            "R2|S1": "R2", "R2|S2": "R2", "S1|S2": "S1"}
    cells = [
        # No recommendation, but the BASELINE relations show R2 beating both S.
        {"support_m": 90.0, "result_state": "INDETERMINATE", "recommended_unit": None,
         "pareto_layer1": ["R2"], "dominance_matrix": full},
        # Winners split: R1 beats only S1, R2 beats only S2 -> no ONE winner.
        {"support_m": 150.0, "result_state": "TIE", "recommended_unit": None,
         "pareto_layer1": ["R1", "R2"],
         "dominance_matrix": {"R1|R2": "~", "R1|S1": "R1", "R1|S2": "~",
                              "R2|S1": "~", "R2|S2": "R2", "S1|S2": "~"}},
        # S2 absent from the matrix (e.g. ineligible): counts as NOT dominated.
        {"support_m": 300.0, "result_state": "RECOMMEND_FOLLOW_UP",
         "recommended_unit": "R1", "pareto_layer1": ["R1"],
         "dominance_matrix": {"R1|R2": "R1", "R1|S1": "R1", "R2|S1": "R2"}},
        # ERROR never satisfies, whatever it carries.
        {"support_m": 600.0, "result_state": "ERROR", "recommended_unit": None,
         "pareto_layer1": ["R1"], "dominance_matrix": full},
    ]
    d = cf.evaluate_expectation(_dom("rough_family", "smooth_family"), cells, _CLS)
    assert [p["satisfied"] for p in d["per_support"]] == [True, False, False, False], d
    assert d["outcome"] == "mixed" and d["satisfied_fraction"] == 0.25, d
    assert d["error_supports"] == [600.0], d
    assert d["declared"] == _dom("rough_family", "smooth_family"), d
    l1 = cf.evaluate_expectation(_in_l1("rough_family"), cells, _CLS)
    assert [p["satisfied"] for p in l1["per_support"]] == [True, True, True, False], l1
    assert cf.evaluate_expectation(_in_l1("rough_family"), cells[:3], _CLS)["outcome"] == "holds"
    sm = cf.evaluate_expectation(_in_l1("smooth_family"), cells, _CLS)
    assert sm["outcome"] == "fails" and sm["satisfied_fraction"] == 0.0, sm
    # The unit types ignore candidate_classes entirely.
    for exp in ({"type": "recommends", "unit": "R1"}, {"type": "non_dominated", "unit": "S1"},
                {"type": "not_sole", "unit": "R1"}):
        assert cf.evaluate_expectation(exp, cells, _CLS) == cf.evaluate_expectation(exp, cells)


def test_multiple_named_expectations_evaluated_and_stored():
    out = _class_run()
    assert _CLASS_CACHE["panel"] == _class_panel(), "the predeclared panel must never be edited"
    refs = _refs(out)
    for entry in _class_panel():
        r = refs[entry["id"]]
        assert sorted(r["expectations"]) == sorted(e["name"] for e in entry["expects"])
        for e in entry["expects"]:
            got = r["expectations"][e["name"]]
            assert got == cf.evaluate_expectation(e, r["cells"], _CLS), (e, got)
            assert got["declared"] == e, got            # verbatim, name included
    # The single `expect` is untouched by the named ones: same result as its named twin.
    rough = refs["rough_ref"]
    assert rough["expectation"]["declared"] == _class_panel()[0]["expect"]

    def undeclared(e):
        return {k: v for k, v in e.items() if k != "declared"}
    assert undeclared(rough["expectation"]) == undeclared(rough["expectations"]["S"])
    # Named-only reference: `expectation` is not_predeclared and it is not counted
    # as confirmation (counts_as_confirmation and the summary read `expect` only).
    smooth = refs["smooth_ref"]
    assert smooth["expectation"]["outcome"] == "not_predeclared", smooth["expectation"]
    assert smooth["counts_as_confirmation"] is False
    s = out["summary"]
    assert s["classes"]["smooth_terrain"]["outcomes"]["not_predeclared"] == 1, s
    assert s["confirmatory_outcomes"] == {"holds": 1, "mixed": 0, "fails": 0,
                                          "not_predeclared": 1}, s
    # A reference without `expects` gets no `expectations` key at all.
    assert all("expectations" not in r for r in _run(adequacy=False)["references"])


def test_class_and_named_expectation_misdeclarations_fail_fast():
    g = _class_grids()
    calls = []
    real_cell, real_ade = cf._run_cell, cf._run_adequacy

    def counting_cell(*a, **k):
        calls.append("cell")
        return real_cell(*a, **k)

    def counting_ade(*a, **k):
        calls.append("adequacy")
        return real_ade(*a, **k)

    def entry(**kw):
        e = {"id": "rough_ref", "class": "rough_terrain", "status": "confirmatory"}
        e.update(kw)
        return e

    three = {"R1": "rough_family", "R2": "rough_family", "S1": "smooth_family"}
    bad = [
        ([entry(expect=_dom("rough_family", "smooth_family"))], None,
         "class `expect` without candidate_classes"),
        ([entry(expects=[dict(_in_l1("rough_family"), name="V")])], None,
         "class `expects` entry without candidate_classes"),
        ([entry(expect=_in_l1("basaltic"))], _CLS, "unknown class"),
        ([entry(expects=[dict(_dom("basaltic", "smooth_family"), name="S")])], _CLS,
         "unknown winner_class"),
        ([entry(expects=[dict(_dom("rough_family", "smooth"), name="S")])], _CLS,
         "unknown loser_class"),
        ([entry(expect=_dom("rough_family", "rough_family"))], _CLS, "winner == loser"),
        ([entry(expect=_in_l1("rough_family"))], three, "candidate S2 has no class"),
        ([entry(expect=None)], three, "candidate S2 has no class (no class expectation)"),
        ([entry(expect=None)], dict(_CLS, S2=""), "empty class name"),
        ([entry(expects=[dict(_in_l1("rough_family"), name="V"),
                         dict(_in_l1("smooth_family"), name="V")])], _CLS,
         "duplicate expectation names"),
        ([entry(expects=[_in_l1("rough_family")])], _CLS, "unnamed expectation"),
        ([entry(expects=dict(_in_l1("rough_family"), name="V"))], _CLS,
         "`expects` not a list"),
        ([entry(expects=[{"name": "N", "type": "not_sole", "unit": "W"}])], _CLS,
         "named unit expectation on a non-candidate"),
    ]
    cf._run_cell, cf._run_adequacy = counting_cell, counting_ade
    try:
        for panel, classes, what in bad:
            try:
                cf.run_reference_panel(g, _DX, panel, _CLS_CANDS, _EXTENT_M, _SUPPORTS,
                                       candidate_classes=classes)
            except ValueError:
                continue
            raise AssertionError(f"misdeclaration accepted: {what}")
        assert calls == [], calls                  # rejected BEFORE anything ran
        # The counter is live: a valid panel does run cells.
        cf.run_reference_panel(g, _DX, [entry(expect=_in_l1("rough_family"))],
                               _CLS_CANDS, _EXTENT_M, _SUPPORTS[:1],
                               candidate_classes=_CLS, adequacy=False)
        assert calls == ["cell"], calls
    finally:
        cf._run_cell, cf._run_adequacy = real_cell, real_ade
    # evaluate_expectation called directly enforces the same class rules.
    for exp, classes in ((_in_l1("rough_family"), None), (_in_l1("basaltic"), _CLS),
                         (_dom("rough_family", "rough_family"), _CLS)):
        try:
            cf.evaluate_expectation(exp, [], classes)
        except ValueError:
            continue
        raise AssertionError(f"evaluate_expectation accepted {exp!r} with {classes!r}")


_V2_TOP_KEYS = {"extent_m", "supports_m", "decision_metrics", "candidates",
                "references", "summary", "note"}
_V2_REF_KEYS = {"id", "class", "status", "counts_as_confirmation", "compared_units",
                "cells", "adequacy", "expectation"}
_V2_CELL_KEYS = {"support_m", "result_state", "recommended_unit", "pareto_layer1",
                 "compared_units", "provenance", "error"}
_NEW_CELL_KEYS = {"pareto_layers", "dominance_matrix"}


def _old_fields_json(out):
    """Only the pre-existing (v2) fields of a panel output, as canonical JSON."""
    o = copy.deepcopy(out)
    o.pop("candidate_classes", None)
    for r in o["references"]:
        r.pop("expectations", None)
        for c in r["cells"]:
            for k in _NEW_CELL_KEYS:
                c.pop(k, None)
    return json.dumps(o, sort_keys=True, allow_nan=False)


def test_v2_style_panel_old_fields_byte_identical_with_new_parameters():
    # Backward compatibility for the frozen v2 experiment: a v2-style panel (single
    # `expect`, no classes) and the SAME panel with candidate classes + named class
    # expectations on every reference produce byte-identical pre-existing fields.
    base = _run()
    panel = _panel()
    for p in panel:
        p["expects"] = [dict(_in_l1("moderate"), name="X_class_in_layer1"),
                        dict(_dom("moderate", "smooth"), name="X_class_beats_Y")]
    classes = {"X": "moderate", "Y": "smooth", "Z": "rough", "unused_id": "rough"}
    extended = _run(panel=panel, candidate_classes=classes)
    assert _old_fields_json(extended) == _old_fields_json(base)
    # The v2-style run carries ONLY the pre-existing keys + the two cell pass-throughs.
    assert set(base) == _V2_TOP_KEYS, sorted(base)
    for r in base["references"]:
        assert set(r) == _V2_REF_KEYS, sorted(r)
        for c in r["cells"]:
            assert set(c) == _V2_CELL_KEYS | _NEW_CELL_KEYS, sorted(c)
    # The extended run adds only what was opted into; the stored class map holds
    # exactly the candidates used (an entry for a non-candidate is ignored).
    assert set(extended) == _V2_TOP_KEYS | {"candidate_classes"}, sorted(extended)
    assert all(set(r) == _V2_REF_KEYS | {"expectations"} for r in extended["references"])
    assert extended["candidate_classes"] == {"X": "moderate", "Y": "smooth", "Z": "rough"}
    # A sole RECOMMEND of X implies X is in layer 1, so the class twin holds too.
    for rid in ("plains_a", "plains_b"):
        assert _refs(extended)[rid]["expectations"]["X_class_in_layer1"]["outcome"] == "holds"
    assert base["summary"]["specificity"]["verdict"] == "specific"
