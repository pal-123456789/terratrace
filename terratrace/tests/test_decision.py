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


def test_eligibility_blocks_water_contaminated_unit():
    unit = {"data_present": True, "support_valid": True, "valid_fraction": 0.98,
            "min_valid_fraction": 0.5, "rights_status": "verified_allowed",
            "zero_fraction": 0.98}
    ok, reason = decision.eligibility(unit)
    assert not ok and "water" in reason.lower()
