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


def _geomorphic_scene():
    from terratrace import synthetic
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    return {
        "ref": base + synthetic.rough_field((64, 64), 0.8, seed=1),
        "near": base + synthetic.rough_field((64, 64), 0.9, seed=2),
        "far": base + synthetic.rough_field((64, 64), 4.0, seed=3),
    }


def test_geomorphic_mode_adds_curvature_and_vrm_axes():
    raw = _geomorphic_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="geomorphic")
    assert pkg["profile"]["decision_metrics"] == "geomorphic"
    assert pkg["profile"]["metrics"][-2:] == ["mean_curvature", "vector_ruggedness"]
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 6
    assert pkg["result_state"] in study.decision.STATES


def test_geomorphic_mode_recommends_closer_unit_and_reports_hurst():
    raw = _geomorphic_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="geomorphic")
    assert pkg["result_state"] == "RECOMMEND_FOLLOW_UP"
    assert pkg["recommended_unit"] == "near"
    gm = pkg["geomorphic_metrics"]
    assert set(gm) == set(raw)
    for u in raw:
        assert "hurst_exponent" in gm[u] and "mean_curvature_median" in gm[u]


def test_core_and_extended_packages_have_no_geomorphic_key():
    # The opt-in mode must not leak into the default/extended packages (keeps
    # their provenance hashes byte-stable).
    raw = _geomorphic_scene()
    rights = {k: "verified_allowed" for k in raw}
    for mode in ("core", "extended"):
        pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                                  target_support_m=10.0, decision_metrics=mode)
        assert "geomorphic_metrics" not in pkg


def test_core_study_hash_is_stable_regression():
    # The gated-build invariant, tested PORTABLY (the absolute hash value is
    # float/NumPy-build dependent, so it is NOT pinned across environments):
    #   1) run_study is deterministic within an environment (same inputs -> same hash);
    #   2) the default package carries NONE of the opt-in blocks, so adding opt-in
    #      modes never perturbs the core study package;
    #   3) the hash is a well-formed 64-char sha256 hex digest.
    pkg = study.run_study()
    h = pkg["package_hash"]
    assert study.run_study()["package_hash"] == h            # deterministic
    for opt_in in ("feature_uncertainty", "previews", "geomorphic_metrics", "bootstrap"):
        assert opt_in not in pkg, opt_in                     # core untouched by opt-in modes
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


def test_feature_uncertainty_and_previews_are_opt_in():
    raw = _geomorphic_scene()
    rights = {k: "verified_allowed" for k in raw}
    # OFF by default -> neither key present (keeps packages/hashes byte-stable).
    off = study.compare_units(raw, rights, 10.0, reference_id="ref", target_support_m=10.0)
    assert "feature_uncertainty" not in off and "previews" not in off
    # vertical_accuracy -> propagated per-unit uncertainty block.
    on = study.compare_units(raw, rights, 10.0, reference_id="ref", target_support_m=10.0,
                             vertical_accuracy={"ref": 3.0, "near": 4.0, "far": 4.0},
                             previews=True)
    fu = on["feature_uncertainty"]
    assert set(fu) == set(raw)
    for uid in raw:
        assert fu[uid]["relief_sigma_m"] > 0 and "slope_sigma_deg" in fu[uid]
    # previews -> one self-contained hillshade PNG data-URI per unit.
    assert set(on["previews"]) == set(raw)
    assert all(v.startswith("data:image/png;base64,") for v in on["previews"].values())
