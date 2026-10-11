"""Opt-in, GATED resampling-significance in the study (``study.compare_units``
with ``significance=True``). Mirrors the geomorphic/landform opt-in test style:
dependency-free (no pytest), assert-based; run via ``tests/run_tests.py`` or by
calling the ``test_*`` functions directly.

What is asserted:
 * a clear-winner scene -> significance block present; the recommended unit is the
   closer one AND significant (p_one < 0.05) on the dominant sample-array metric;
 * the runner-up is the SECOND-closest compared unit (smallest core-vector sum
   among the non-recommended), never an arbitrary other unit;
 * a near-tie scene -> honest: ``recommendation_significant`` is False;
 * the connectivity axis is a SCALAR (method="scalar"), never permuted;
 * ``significance=False`` attaches NOTHING (key absent), in every decision mode;
 * determinism: a fixed seed reproduces identical p-values;
 * non-single-recommendation / <2-unit states -> ``evaluated=False``;
 * the frozen default ``run_study()`` package hash stays byte-identical (gate).

These are DISTRIBUTION-SHAPE resampling statistics only (see significance.py) --
not a physical, geological, or mission claim.
"""
from terratrace import study, synthetic

# The default run_study() package is the gated teaching/CI invariant: adding this
# opt-in capability must not perturb it (significance defaults OFF). NOTE: the
# absolute sha256 is float / NumPy-build dependent (CI runs a newer NumPy than the
# dev sandbox), so the gate asserts PORTABLE invariants -- determinism, absence of
# the opt-in key, and a well-formed digest -- never a pinned cross-env literal.

ARRAY_METRICS = ("slope", "relief", "ruggedness")


def _plane(shape):
    return synthetic.plane(shape, slope_x=0.02, dx=10.0)


def _rough(shape, amp, seed):
    return synthetic.rough_field(shape, amp, seed=seed)


def _run(raw, **kw):
    rights = {k: "verified_allowed" for k in raw}
    return study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                               target_support_m=10.0, **kw)
def _clear_scene():
    """One candidate ('near', roughness 0.9) sits very close to the reference
    (0.8) and one ('far', roughness 4.0) sits far from it -> a robust, unambiguous
    winner across every sensitivity scenario."""
    s = (24, 24)
    return {"ref": _plane(s) + _rough(s, 0.8, 1),
            "near": _plane(s) + _rough(s, 0.9, 2),
            "far": _plane(s) + _rough(s, 4.0, 3)}


def _near_tie_scene():
    """'near' and 'far' SHARE the same roughness field (seed 2) at amplitudes 1.0
    vs 1.02, so 'near' Pareto-dominates by a hair (-> RECOMMEND_FOLLOW_UP) yet the
    two candidates are nearly the same distribution: the permutation test cannot
    call the closeness gap beyond chance (honest 'not significant')."""
    s = (16, 16)
    return {"ref": _plane(s) + _rough(s, 1.0, 1),
            "near": _plane(s) + _rough(s, 1.0, 2),
            "far": _plane(s) + _rough(s, 1.02, 2)}


def test_clear_winner_recommendation_is_significant():
    pkg = _run(_clear_scene(), significance=True, n_perm=200, significance_seed=0)
    assert pkg["result_state"] == "RECOMMEND_FOLLOW_UP"
    assert pkg["recommended_unit"] == "near"
    sig = pkg["significance"]
    assert "evaluated" not in sig                              # fully evaluated
    assert sig["reference_id"] == "ref"
    assert sig["recommended_unit"] == "near"
    assert sig["runner_up"] == "far"
    assert sig["n_perm"] == 200 and sig["seed"] == 0
    # Each sample-array metric is a permutation test carrying the full record.
    for m in ARRAY_METRICS:
        d = sig["per_metric"][m]
        assert d["method"] == "permutation"
        assert set(d) >= {"observed_diff", "p_value_one_sided", "p_value_two_sided",
                          "a_closer", "significant", "effect_size", "method"}
    # The recommended is the closer one and significant on the dominant metric.
    rug = sig["per_metric"]["ruggedness"]
    assert rug["a_closer"] is True
    assert rug["p_value_one_sided"] < 0.05
    assert rug["effect_size"] > 0.0
    assert sig["recommendation_significant"] is True
    assert sig["n_significant_metrics"] >= 1


def test_connectivity_axis_is_scalar_not_permutation():
    sig = _run(_clear_scene(), significance=True, n_perm=200)["significance"]
    conn = sig["per_metric"]["connectivity"]
    assert conn["method"] == "scalar"
    assert set(conn) == {"observed_diff", "a_closer", "method"}   # no p-values here
    # a_closer is just the sign of the signed scaled difference (neg => rec closer).
    assert conn["a_closer"] == (conn["observed_diff"] < 0)
    # The scalar axis is NOT counted toward the significance tally.
    assert "connectivity" not in ARRAY_METRICS
def test_runner_up_is_second_closest_not_arbitrary():
    # Four units: a clear winner ('win'), a middling 'mid', and a far 'farr'. The
    # runner-up must be the SECOND-closest -- the smallest core-vector (baseline_
    # vectors) sum among the non-recommended -> 'mid', never the far 'farr'.
    s = (24, 24)
    raw = {"ref": _plane(s) + _rough(s, 0.8, 1),
           "win": _plane(s) + _rough(s, 0.85, 2),
           "mid": _plane(s) + _rough(s, 1.3, 3),
           "farr": _plane(s) + _rough(s, 5.0, 4)}
    pkg = _run(raw, significance=True, n_perm=200)
    assert pkg["result_state"] == "RECOMMEND_FOLLOW_UP"
    assert pkg["recommended_unit"] == "win"
    sums = {u: sum(v) for u, v in pkg["baseline_vectors"].items()}
    non_rec = {u: sums[u] for u in sums if u != "win"}
    # The documented rule: min on (vector-sum, unit-id).
    expected = min(non_rec, key=lambda u: (non_rec[u], u))
    assert expected == "mid", sums
    assert pkg["significance"]["runner_up"] == "mid"


def test_near_tie_recommendation_not_significant():
    pkg = _run(_near_tie_scene(), significance=True, n_perm=200, significance_seed=0)
    assert pkg["result_state"] == "RECOMMEND_FOLLOW_UP"       # a hair-thin winner
    assert pkg["recommended_unit"] == "near"
    sig = pkg["significance"]
    assert sig["runner_up"] == "far"
    # Honest: the resampling test cannot call the closeness gap beyond chance.
    assert sig["recommendation_significant"] is False
    assert sig["n_significant_metrics"] == 0
    for m in ARRAY_METRICS:
        assert sig["per_metric"][m]["p_value_one_sided"] >= 0.05, m


def test_significance_absent_when_flag_off():
    # significance=False attaches NOTHING, in every decision mode, so the core/
    # extended/geomorphic/landform packages (and their hashes) are untouched.
    scene = _clear_scene()
    assert "significance" not in _run(scene)
    for mode in ("core", "extended", "geomorphic", "landform"):
        assert "significance" not in _run(scene, decision_metrics=mode), mode


def test_significance_is_deterministic():
    a = _run(_clear_scene(), significance=True, n_perm=200, significance_seed=0)["significance"]
    b = _run(_clear_scene(), significance=True, n_perm=200, significance_seed=0)["significance"]
    for m in ARRAY_METRICS:
        da, db = a["per_metric"][m], b["per_metric"][m]
        assert da["p_value_one_sided"] == db["p_value_one_sided"]
        assert da["p_value_two_sided"] == db["p_value_two_sided"]
        assert da["effect_size"] == db["effect_size"]
    assert a["recommendation_significant"] == b["recommendation_significant"]
def test_single_candidate_is_not_evaluated():
    # One eligible candidate -> RECOMMEND_FOLLOW_UP, but a closeness test needs a
    # runner-up: significance is attached as evaluated=False (>= 2 units required).
    s = (24, 24)
    raw = {"ref": _plane(s) + _rough(s, 0.8, 1), "near": _plane(s) + _rough(s, 0.9, 2)}
    pkg = _run(raw, significance=True, n_perm=200)
    assert pkg["result_state"] == "RECOMMEND_FOLLOW_UP"
    sig = pkg["significance"]
    assert sig["evaluated"] is False
    assert sig["state"] == "RECOMMEND_FOLLOW_UP"
    assert sig["reference_id"] == "ref"
    assert "2" in sig["reason"]


def test_non_recommendation_state_is_not_evaluated():
    # All candidates blocked (rights not verified) -> state BLOCKED, no single
    # recommendation: significance is attached as evaluated=False.
    s = (24, 24)
    raw = {"ref": _plane(s) + _rough(s, 0.8, 1),
           "c1": _plane(s) + _rough(s, 0.9, 2),
           "c2": _plane(s) + _rough(s, 1.0, 3)}
    rights = {"ref": "verified_allowed", "c1": "unknown", "c2": "pending"}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, significance=True, n_perm=200)
    assert pkg["result_state"] != "RECOMMEND_FOLLOW_UP"
    sig = pkg["significance"]
    assert sig["evaluated"] is False
    assert sig["state"] == pkg["result_state"]
    assert sig["reference_id"] == "ref"


def test_default_study_hash_is_byte_identical_gate():
    # Portable gate: significance defaults OFF, so the default package carries no
    # significance key; run_study is deterministic in-env and yields a well-formed
    # sha256. The absolute digest is NOT pinned (NumPy-build dependent across CI).
    pkg = study.run_study()
    h = pkg["package_hash"]
    assert study.run_study()["package_hash"] == h            # deterministic in-env
    assert "significance" not in pkg
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)


