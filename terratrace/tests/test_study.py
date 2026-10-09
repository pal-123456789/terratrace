"""End-to-end study fixtures."""
from terratrace import study


def test_study_runs_and_has_contract_keys():
    pkg = study.run_study()
    for key in ("profile", "result_state", "baseline_vectors", "scenario_vectors",
                "transfer_gap_ledger", "draft_protocol", "evidence_graph",
                "eligibility", "package_hash"):
        assert key in pkg, key
    assert pkg["result_state"] in study.decision.STATES


def test_blocked_unit_is_ineligible():
    pkg = study.run_study()
    assert pkg["eligibility"]["earth_blocked"]["eligible"] is False
    assert "earth_blocked" not in pkg["baseline_vectors"]


def test_close_unit_dominates_far_unit():
    pkg = study.run_study()
    close = pkg["baseline_vectors"]["earth_close"]
    far = pkg["baseline_vectors"]["earth_far"]
    assert all(c <= f for c, f in zip(close, far)), (close, far)
    assert any(c < f for c, f in zip(close, far)), (close, far)


def test_result_is_deterministic():
    a = study.run_study()["package_hash"]
    b = study.run_study()["package_hash"]
    assert a == b


def test_prohibited_claims_present():
    pkg = study.run_study()
    assert any("rover" in c.lower() or "traversab" in c.lower() or "route" in c.lower()
               for c in pkg["prohibited_claims"])


def test_all_blocked_candidates_yield_blocked_state():
    from terratrace import synthetic
    raw = {
        "mars_reference": synthetic.plane((48, 48), 0.12, 0.05),
        "e1": synthetic.plane((48, 48), 0.11, 0.06),
        "e2": synthetic.plane((48, 48), 0.30, 0.02),
    }
    rights = {"mars_reference": "verified_allowed", "e1": "unknown", "e2": "pending"}
    pkg = study.compare_units(raw, rights, native_posting_m=25.0, target_support_m=100.0)
    assert pkg["result_state"] == "BLOCKED"
    assert pkg["recommended_unit"] is None
    assert pkg["baseline_vectors"] == {}


def test_evidence_graph_has_eligibility_nodes():
    pkg = study.run_study()
    ids = {n["id"] for n in pkg["evidence_graph"]["nodes"]}
    assert any(i.startswith("c:elig:") for i in ids)
    assert "c:result" in ids and "c:protocol" in ids


def test_extended_decision_mode_adds_two_dimensions():
    from terratrace import synthetic
    raw = {
        "mars_reference": synthetic.plane((64, 64), 0.12, 0.05) + synthetic.rough_field((64, 64), 0.6, 1),
        "e1": synthetic.plane((64, 64), 0.11, 0.06) + synthetic.rough_field((64, 64), 0.65, 2),
        "e2": synthetic.plane((64, 64), 0.30, 0.02) + synthetic.rough_field((64, 64), 2.2, 3),
    }
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=25.0, target_support_m=100.0,
                              decision_metrics="extended")
    assert pkg["profile"]["decision_metrics"] == "extended"
    assert len(pkg["profile"]["metrics"]) == 6
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 6
    assert pkg["result_state"] in study.decision.STATES
