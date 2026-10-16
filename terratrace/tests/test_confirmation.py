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
