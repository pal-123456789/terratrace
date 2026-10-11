"""Tests for terratrace.confidence (non-composite decision confidence)."""
import copy

from terratrace import confidence

VALID_VERDICTS = {"robust", "qualified", "fragile", "tie", "indeterminate",
                  "blocked", "not_comparable", "unverified"}


def _pkg(state="RECOMMEND_FOLLOW_UP", unit="earth_close", nondom=None,
         significant=None, runner_up="earth_far"):
    """Hand-crafted study package; blocks appear only when values are given."""
    pkg = {"result_state": state, "recommended_unit": unit}
    if nondom is not None:
        pkg["bootstrap"] = {"n_boot": 50, "seed": 0, "decisive_freq": 1.0,
                            "units": {unit: {"nondominated_freq": nondom,
                                             "clear_winner_freq": nondom}}}
    if significant is not None:
        pkg["significance"] = {
            "recommended_unit": unit, "runner_up": runner_up,
            "recommendation_significant": significant,
            "per_metric": {
                "slope": {"p_value_one_sided": 0.01, "a_closer": True,
                          "significant": True},
                "relief": {"p_value_one_sided": 0.03, "a_closer": True,
                           "significant": True}},
            "n_significant_metrics": 2}
    return pkg


def _sens(stable):
    """Ablation report shaped like sensitivity.ablation_report(...)."""
    return {"lens": {"recommendation_stable": stable},
            "support": None, "overall_stable": stable,
            "note": "test ablation"}


def test_all_positive_is_robust():
    out = confidence.decision_confidence(_pkg(nondom=0.95, significant=True),
                                         _sens(True))
    assert out["verdict"] == "robust"
    assert out["caveats"] == []
    b = out["signals"]["bootstrap_non_domination"]
    assert b["evaluated"] is True and b["positive"] is True and b["value"] == 0.95
    assert out["signals"]["significance_vs_runner_up"]["significant"] is True
    assert out["signals"]["lens_stability"]["stable"] is True
    assert out["state"] == "RECOMMEND_FOLLOW_UP"
    assert out["recommended_unit"] == "earth_close"

def test_significant_false_is_fragile():
    out = confidence.decision_confidence(_pkg(nondom=0.95, significant=False),
                                         _sens(True))
    assert out["verdict"] == "fragile"
    sg = out["signals"]["significance_vs_runner_up"]
    assert sg["evaluated"] is True and sg["significant"] is False
    assert out["caveats"] == []


def test_low_bootstrap_is_fragile():
    # nondomination < 0.5 is a negative signal on its own.
    out = confidence.decision_confidence(_pkg(nondom=0.2))
    assert out["verdict"] == "fragile"
    b = out["signals"]["bootstrap_non_domination"]
    assert b["evaluated"] is True and b["positive"] is False


def test_only_bootstrap_high_is_qualified():
    out = confidence.decision_confidence(_pkg(nondom=0.9))
    assert out["verdict"] == "qualified"
    assert out["signals"]["bootstrap_non_domination"]["evaluated"] is True
    assert out["signals"]["significance_vs_runner_up"]["evaluated"] is False
    assert out["signals"]["lens_stability"]["evaluated"] is False
    assert set(out["caveats"]) == {"significance_vs_runner_up not evaluated",
                                   "lens_stability not evaluated"}
    assert len(out["caveats"]) == 2


def test_weak_bootstrap_alone_is_qualified():
    out = confidence.decision_confidence(_pkg(nondom=0.65))
    assert out["verdict"] == "qualified"
    b = out["signals"]["bootstrap_non_domination"]
    assert b["evaluated"] is True and b["positive"] is None  # weak band


def test_weak_bootstrap_with_significance_is_qualified():
    # Two evaluated, none negative, but one weak -> qualified (not robust).
    out = confidence.decision_confidence(_pkg(nondom=0.6, significant=True))
    assert out["verdict"] == "qualified"


def test_nothing_evaluated_is_unverified():
    pkg = {"result_state": "RECOMMEND_FOLLOW_UP", "recommended_unit": "earth_close"}
    out = confidence.decision_confidence(pkg)
    assert out["verdict"] == "unverified"
    assert len(out["caveats"]) == 3
    for name in confidence.SIGNAL_NAMES:
        assert out["signals"][name]["evaluated"] is False

def test_tie_mirrors_state():
    pkg = {"result_state": "TIE", "recommended_unit": None,
           "bootstrap": {"n_boot": 50, "units": {}}}
    out = confidence.decision_confidence(pkg)
    assert out["verdict"] == "tie"
    assert out["state"] == "TIE"
    assert out["recommended_unit"] is None


def test_other_states_mirror():
    for state, verdict in (("INDETERMINATE", "indeterminate"),
                           ("BLOCKED", "blocked"),
                           ("NOT_COMPARABLE", "not_comparable")):
        out = confidence.decision_confidence(
            {"result_state": state, "recommended_unit": None})
        assert out["verdict"] == verdict


def test_unknown_or_missing_state_is_unverified():
    assert confidence.decision_confidence({})["verdict"] == "unverified"
    assert confidence.decision_confidence(
        {"result_state": "WAT"})["verdict"] == "unverified"


def test_significance_block_without_flag_not_evaluated():
    pkg = _pkg(nondom=0.9)
    pkg["significance"] = {"runner_up": "earth_far", "per_metric": {}}
    out = confidence.decision_confidence(pkg)
    assert out["signals"]["significance_vs_runner_up"]["evaluated"] is False


def test_significance_reports_weakest_p():
    out = confidence.decision_confidence(_pkg(nondom=0.95, significant=True))
    # weakest == max one-sided p across per_metric (0.01, 0.03) -> 0.03
    assert out["signals"]["significance_vs_runner_up"]["p_value_one_sided"] == 0.03


def test_input_not_mutated():
    pkg = _pkg(nondom=0.95, significant=True)
    sens = _sens(True)
    pkg_before = copy.deepcopy(pkg)
    sens_before = copy.deepcopy(sens)
    confidence.decision_confidence(pkg, sens)
    assert pkg == pkg_before
    assert sens == sens_before


def test_integration_real_study():
    from terratrace import study
    pkg = study.run_study(n_boot=60)
    out = confidence.decision_confidence(pkg)
    assert out["verdict"] in VALID_VERDICTS
    b = out["signals"]["bootstrap_non_domination"]
    assert b["evaluated"] is True
    assert b["value"] is not None and 0.0 <= b["value"] <= 1.0
    unit = pkg["recommended_unit"]
    assert b["value"] == pkg["bootstrap"]["units"][unit]["nondominated_freq"]
    assert out["state"] == pkg["result_state"]

