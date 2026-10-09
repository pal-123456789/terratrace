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
