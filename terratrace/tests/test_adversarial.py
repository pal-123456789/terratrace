"""Dependency-free oracles for the adversarial robustness stress-test.

This is EXPLORATORY-METHOD VALIDATION: it checks that the stress test honestly
reports the trust bounds of a matched-footprint recommendation -- that a clear
winner survives most perturbations, that a near-tie does NOT earn a robust verdict,
and that dropping the winning candidate is recorded. It is NOT a scientific claim
about Mars and NOT confirmatory evidence; like the stress test itself it is kept
separate from the frozen synthetic ground-truth validation.

It reuses the SAME rough-core / smooth-apron synthetic fixture as
``test_matched_benchmark`` (a rough core inside a smooth apron; a uniformly smooth
candidate; a uniformly rough candidate), matched at the core extent so B_rough is
the morphologically correct analog.

Plain ``def test_*()``, assert-based, no pytest, no network. Deterministic seeds.
"""
import json

import numpy as np

from terratrace import adversarial as adv, synthetic

_N = 400
_DX = 30.0
_CORE_RADIUS_M = 700.0
_EXTENT_M = 1200.0
_SUPPORT_M = 90.0


def _rough_core_reference():
    """A rough core (amplitude 25) inside a smooth apron (amplitude 4) -- identical to
    the matched-benchmark fixture's reference. At the core extent it reads as rough."""
    ii, jj = np.indices((_N, _N))
    r = np.hypot(ii - _N // 2, jj - _N // 2) * _DX
    core = r < _CORE_RADIUS_M
    X = synthetic.rough_field((_N, _N), amplitude=25.0, seed=1)
    Y = synthetic.rough_field((_N, _N), amplitude=4.0, seed=1)
    return np.where(core, X, Y)


def _clear_scene():
    """Clear winner: at the core extent the reference is rough, so the rough candidate
    is the correct analog by a wide (6x roughness) margin."""
    return {
        "ref": _rough_core_reference(),
        "A_smooth": synthetic.rough_field((_N, _N), amplitude=4.0, seed=2),
        "B_rough": synthetic.rough_field((_N, _N), amplitude=25.0, seed=3),
    }


def _near_tie_scene():
    """Near-tie: two candidates that are nearly identical to the reference's core
    roughness (both rough, a tiny 25.0 vs 25.3 amplitude difference), so the engine
    cannot distinguish them and the baseline is a TIE (no analog recommended)."""
    return {
        "ref": _rough_core_reference(),
        "C1": synthetic.rough_field((_N, _N), amplitude=25.0, seed=11),
        "C2": synthetic.rough_field((_N, _N), amplitude=25.3, seed=12),
    }


def test_clear_winner_is_mostly_stable():
    # Oracle: a 6x roughness gap makes B_rough the baseline analog, and most
    # scientifically-justified perturbations leave that recommendation intact.
    s = adv.stress_test(_clear_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M,
                        decision_metrics="core", seed=0)
    assert s["baseline"]["recommended_unit"] == "B_rough", s["baseline"]
    assert s["baseline"]["result_state"] == "RECOMMEND_FOLLOW_UP", s["baseline"]
    assert s["stable_fraction"] >= 0.6, s["stable_fraction"]
    assert s["verdict"] != "fragile", s["verdict"]
    # the five documented families are all exercised
    assert {p["family"] for p in s["perturbations"]} == set(adv.FAMILIES), s["perturbations"]


def test_near_tie_is_fragile():
    # Oracle: two indistinguishable candidates give a TIE baseline (no analog), and the
    # stress test must NOT certify that as robust -- it reports change, because when the
    # tie is forced (e.g. by dropout) different conditions pick different "winners".
    clear = adv.stress_test(_clear_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M, seed=0)
    tie = adv.stress_test(_near_tie_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M, seed=0)
    # A TIE: baseline recommends nothing (handled gracefully as None).
    assert tie["baseline"]["recommended_unit"] is None, tie["baseline"]
    assert tie["baseline"]["result_state"] == "TIE", tie["baseline"]
    # More change than the clear winner: reversing conditions are present...
    assert len(tie["reversing_conditions"]) > 0, tie["reversing_conditions"]
    # ...and perturbations resolve the tie into CONFLICTING definite winners,
    # so the apparent analog is an artifact of the conditions.
    definite = {p["recommended_unit"] for p in tie["perturbations"]
                if p["recommended_unit"] is not None}
    assert len(definite) >= 2, definite
    # A near-tie is therefore never "robust"; here it is explicitly "fragile".
    assert tie["verdict"] == "fragile", tie["verdict"]
    assert tie["verdict"] != clear["verdict"] or tie["verdict"] != "robust"


def test_candidate_dropout_removes_the_winner():
    # Oracle: dropping the recommended unit yields a recommendation that is NOT the
    # dropped unit (it is gone), while dropping a loser leaves the winner in place.
    s = adv.stress_test(_clear_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M, seed=0)
    winner = s["baseline"]["recommended_unit"]
    assert winner == "B_rough", s["baseline"]
    drops = [p for p in s["perturbations"] if p["family"] == "candidate_dropout"]
    assert drops, "candidate_dropout perturbation must be recorded"
    drop_winner = [p for p in drops if p["label"] == "drop:" + winner]
    assert len(drop_winner) == 1, drops
    assert drop_winner[0]["recommended_unit"] != winner, drop_winner[0]
    assert drop_winner[0]["changed"] is True, drop_winner[0]
    assert drop_winner[0]["label"] in s["reversing_conditions"], s["reversing_conditions"]
    # dropping the loser (A_smooth) must keep the winner and count as unchanged
    drop_loser = [p for p in drops if p["label"] != "drop:" + winner]
    assert drop_loser and all(p["recommended_unit"] == winner and p["changed"] is False
                              for p in drop_loser), drop_loser


def test_contract_keys_json_and_determinism():
    s = adv.stress_test(_clear_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M, seed=0)
    for key in ("baseline", "perturbations", "n_perturbations", "n_changed",
                "stable_fraction", "reversing_conditions", "verdict"):
        assert key in s, key
    for bkey in ("recommended_unit", "result_state", "extent_m", "support_m"):
        assert bkey in s["baseline"], bkey
    assert 0.0 <= s["stable_fraction"] <= 1.0, s["stable_fraction"]
    assert s["n_changed"] == len(s["reversing_conditions"]), s
    assert s["n_perturbations"] == len(s["perturbations"]), s
    for p in s["perturbations"]:
        assert {"family", "label", "recommended_unit", "result_state", "changed"} <= set(p), p
        assert isinstance(p["changed"], bool), p
        assert p["family"] in adv.FAMILIES, p
        assert isinstance(p["label"], str) and p["label"], p
    # JSON round-trips without loss of the decision-relevant fields
    back = json.loads(json.dumps(s))
    assert back["verdict"] == s["verdict"]
    assert back["stable_fraction"] == s["stable_fraction"]
    assert back["perturbations"] == s["perturbations"]
    # deterministic given the seed (two independent runs are identical)
    s2 = adv.stress_test(_clear_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M, seed=0)
    assert s["perturbations"] == s2["perturbations"], "stress test must be deterministic"
    assert s["stable_fraction"] == s2["stable_fraction"] and s["verdict"] == s2["verdict"]


def test_default_study_hash_unchanged_by_this_module():
    # The stress test WRAPS compare_units with throw-away perturbed inputs; it must not
    # perturb the gated default study package or its reproducibility hash.
    from terratrace import study
    h = study.run_study()["package_hash"]
    assert len(h) == 64 and all(ch in "0123456789abcdef" for ch in h), h
    # exercising the module (which internally runs many compare_units calls)...
    adv.stress_test(_clear_scene(), _DX, "ref", _EXTENT_M, _SUPPORT_M, seed=0)
    # ...leaves the default study hash exactly as it was.
    assert study.run_study()["package_hash"] == h, "module must not perturb the default study"
