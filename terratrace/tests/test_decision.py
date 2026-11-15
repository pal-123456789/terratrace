"""Decision-logic fixtures."""
from terratrace import decision


def test_dominates():
    assert decision.dominates((0.1, 0.1), (0.2, 0.2))
    assert not decision.dominates((0.1, 0.3), (0.2, 0.2))
    assert not decision.dominates((0.2, 0.2), (0.2, 0.2))


def test_non_dominated_set():
    vecs = {"a": (0.1, 0.5), "b": (0.5, 0.1), "c": (0.6, 0.6)}
    nd = decision.non_dominated(vecs)
    assert nd == {"a", "b"}         # c is dominated by both


def test_eligibility_blocks_unknown_rights():
    unit = {"data_present": True, "support_valid": True, "valid_fraction": 0.9,
            "min_valid_fraction": 0.5, "rights_status": "unknown"}
    ok, reason = decision.eligibility(unit)
    assert not ok and "rights" in reason


def test_resolve_state_recommends_stable_winner():
    base = {"a": (0.1, 0.1), "b": (0.4, 0.4)}
    scenarios = [base, {"a": (0.12, 0.09), "b": (0.38, 0.42)}]
    state, rec, flips = decision.resolve_state(base, scenarios)
    assert state == "RECOMMEND_FOLLOW_UP"
    assert rec == "a"


def test_resolve_state_tie_when_no_dominance():
    base = {"a": (0.1, 0.5), "b": (0.5, 0.1)}
    scenarios = [base, {"a": (0.1, 0.5), "b": (0.5, 0.1)}]
    state, rec, flips = decision.resolve_state(base, scenarios)
    assert state == "TIE"
    assert rec is None


def test_eligibility_allowlist_fails_closed():
    def unit(status):
        return {"data_present": True, "support_valid": True, "valid_fraction": 0.9,
                "min_valid_fraction": 0.5, "rights_status": status}
    for bad in ("unknown", "no", "pending", "verified", "", None):
        ok, reason = decision.eligibility(unit(bad))
        assert not ok and "rights" in reason, bad
    ok, _ = decision.eligibility(unit("verified_allowed"))
    assert ok


def test_non_dominated_excludes_nan_vectors():
    vecs = {"a": (0.1, 0.1), "b": (float("nan"), 0.2), "c": (0.5, 0.5)}
    nd = decision.non_dominated(vecs)
    assert "b" not in nd            # NaN vector cannot be non-dominated
    assert "a" in nd and "c" not in nd


def test_pairwise_flip_excludes_baseline_from_denominator():
    base = {"a": (0.1, 0.1), "b": (0.4, 0.4)}
    # one non-baseline scenario that fully flips both metrics for the pair
    flip = {"a": (0.4, 0.4), "b": (0.1, 0.1)}
    flips = decision.pairwise_flip_matrix([base, flip])
    assert abs(flips["a|b"] - 1.0) < 1e-9     # 2/2 metric comparisons flipped


def test_pairwise_flip_single_scenario_is_empty():
    assert decision.pairwise_flip_matrix([{"a": (0.1,), "b": (0.2,)}]) == {}


# --------------------------------------------------------------- the undefined normalisation
#
# The axial normalisation is |value - reference| / |reference|, and a reference descriptor can be
# exactly 0 -- a landform or class fraction may legitimately be 0 for the reference window while
# being non-zero elsewhere. The ratio is then undefined, and the tests below pin what the engine
# does about it. The case matters more than its size suggests because of the fixture directly
# above: non_dominated EXCLUDES non-finite vectors, so a NaN does not fail here, it deletes a
# candidate and returns a ranking computed from fewer units than the caller passed in.

def test_axial_fractional_distance_defines_the_zero_cases_explicitly():
    assert decision.axial_fractional_distance(0.0, 0.0) == 0.0, (
        "an exact agreement is a distance of zero; any other value would invent a scale")
    assert abs(decision.axial_fractional_distance(2.0, 3.0) - 0.5) < 1e-15
    # signed descriptors: the reference's magnitude sets the scale in both directions
    assert abs(decision.axial_fractional_distance(-2.0, -3.0) - 0.5) < 1e-15
    assert abs(decision.axial_fractional_distance(-2.0, 3.0) - 2.5) < 1e-15


def test_axial_fractional_distance_refuses_every_undefined_case():
    for ref, val in ((0.0, 1.0), (0.0, -1.0), (float("nan"), 1.0), (1.0, float("nan")),
                     (float("inf"), 1.0), (1.0, float("inf"))):
        raised = False
        try:
            decision.axial_fractional_distance(ref, val)
        except decision.UndefinedNormalisation:
            raised = True
        assert raised, (
            f"reference={ref!r}, value={val!r} is undefined and must refuse; a returned number "
            f"here is either an invented scale or a NaN that deletes a candidate downstream")


def test_the_refusal_names_the_axis_it_could_not_normalise():
    raised = ""
    try:
        decision.axial_fractional_distance(0.0, 4.0, axis="class_fraction_peak")
    except decision.UndefinedNormalisation as exc:
        raised = str(exc)
    assert "class_fraction_peak" in raised, (
        "a refusal that does not say WHICH axis is undefined sends the reader back to the source")


def test_the_refusal_is_load_bearing_not_decorative():
    """Show the consequence the refusal exists to prevent, using the engine's own rule.

    ``non_dominated`` drops any unit carrying a non-finite distance, without reporting it. So if the
    axial normalisation had emitted a NaN instead of refusing, this is exactly what a caller would
    have received: a Pareto set missing a unit it never asked to exclude, and no error.
    """
    survivors = decision.non_dominated(
        {"a": (0.1, 0.1), "b": (float("nan"), 0.2), "c": (0.5, 0.5)})
    assert survivors == {"a"}, (
        "if this ever stops holding, the silent-drop hazard is gone and the axial refusal can be "
        "revisited -- until then it is the thing standing between a zero reference and a ranking "
        "computed over the wrong units")


def test_a_zero_reference_axis_refuses_instead_of_dropping_the_candidate():
    from terratrace import lunar_adversarial as la
    unit_axes = {
        "ref": {"mean_slope_deg": 0.0, "mean_relief3_m": 5.0, "elev_std_m": 3.0},
        "cand": {"mean_slope_deg": 1.5, "mean_relief3_m": 6.0, "elev_std_m": 4.0},
    }
    raised = ""
    try:
        la.fractional_distance(unit_axes, "ref")
    except decision.UndefinedNormalisation as exc:
        raised = str(exc)
    assert "mean_slope_deg" in raised and "cand" in raised, (
        "the panel must refuse a zero-reference axis, and say which axis and which unit")


def test_a_laid_out_panel_still_produces_a_finite_distance_vector():
    """The published path is unchanged: real axes are strictly positive, so nothing refuses."""
    import math

    from terratrace import lunar_adversarial as la
    unit_axes = {
        "ref": {"mean_slope_deg": 12.0, "mean_relief3_m": 30.0, "elev_std_m": 8.0},
        "near": {"mean_slope_deg": 11.0, "mean_relief3_m": 31.0, "elev_std_m": 8.5},
        "far": {"mean_slope_deg": 30.0, "mean_relief3_m": 90.0, "elev_std_m": 25.0},
    }
    rows = la.fractional_distance(unit_axes, "ref")
    assert all(math.isfinite(x) for r in rows.values() for x in r), (
        "no distance reaching the Pareto rule may be non-finite")
    assert la.layer1(unit_axes, "ref") == ["near"]


def test_an_axis_that_agrees_exactly_at_zero_is_a_zero_distance():
    from terratrace import lunar_adversarial as la
    unit_axes = {
        "ref": {"mean_slope_deg": 0.0, "mean_relief3_m": 5.0, "elev_std_m": 3.0},
        "cand": {"mean_slope_deg": 0.0, "mean_relief3_m": 7.0, "elev_std_m": 4.0},
    }
    rows = la.fractional_distance(unit_axes, "ref")
    assert rows["cand"][0] == 0.0
    assert abs(rows["cand"][1] - 0.4) < 1e-12
