"""Decision-sensitivity / ablation fixtures (synthetic, offline, dependency-free).

These mirror the clear-winner scenes used by test_study / test_batch and check
that the robustness ablation agrees the recommendation survives a change of
decision lens and common support. This is a robustness diagnostic over the
map-scale morphology screen, not a new scientific claim.
"""
import numpy as np

from terratrace import sensitivity, synthetic

# Sourced through the engine (sensitivity imports study, study imports decision)
# so the valid-state vocabulary never drifts from the real contract.
VALID_STATES = set(sensitivity.study.decision.STATES)

_L = 10.0


def _clear_winner_scene(n=64, L=_L):
    """Reference = gently sloped rough plane; 'near' is statistically like the
    reference; 'far' is much rougher -- an unambiguous, deterministic winner."""
    base = synthetic.plane((n, n), slope_x=0.02, dx=L)
    raw = {
        "ref":  base + synthetic.rough_field((n, n), 0.8, seed=1),
        "near": base + synthetic.rough_field((n, n), 0.9, seed=2),
        "far":  base + synthetic.rough_field((n, n), 4.0, seed=3),
    }
    for v in raw.values():
        assert v.shape == (n, n) and np.all(np.isfinite(v))
    rights = {k: "verified_allowed" for k in raw}
    return raw, rights


def test_lens_ablation_is_stable_on_clear_winner():
    raw, rights = _clear_winner_scene()
    rep = sensitivity.lens_ablation(raw, rights, native_posting_m=_L,
                                    reference_id="ref", target_support_m=_L)
    # 'near' is the sole recommended analog under every lens that recommends.
    assert rep["recommendation_stable"] is True
    assert rep["recommended_units"] == ["near"]
    # all three lenses ran and produced a valid STATE.
    assert set(rep["per_lens"]) == {"core", "extended", "geomorphic"}
    for lens, entry in rep["per_lens"].items():
        assert entry["result_state"] in VALID_STATES, (lens, entry)
    assert rep["n_recommend"] >= 1


def test_support_ablation_is_stable_across_supports():
    raw, rights = _clear_winner_scene()
    supports = (10.0, 20.0)
    rep = sensitivity.support_ablation(raw, rights, native_posting_m=_L,
                                       reference_id="ref", supports=supports)
    assert set(rep["per_support"]) == set(supports)        # one entry per support
    for s, entry in rep["per_support"].items():
        assert entry["state"] in VALID_STATES, (s, entry)
    assert isinstance(rep["recommendation_stable"], bool)
    assert rep["recommendation_stable"] is True            # clear winner -> stable
    assert rep["recommended_units"] == ["near"]


def test_ablation_report_overall_stable_on_clear_winner():
    raw, rights = _clear_winner_scene()
    rep = sensitivity.ablation_report(raw, rights, native_posting_m=_L,
                                      reference_id="ref", target_support_m=_L,
                                      supports=(10.0, 20.0))
    for key in ("lens", "support", "overall_stable", "note"):
        assert key in rep, key
    assert rep["overall_stable"] is True
    assert rep["lens"]["recommendation_stable"] is True
    assert rep["support"] is not None
    assert rep["support"]["recommendation_stable"] is True
    assert isinstance(rep["note"], str) and rep["note"].strip()


def test_ablation_report_without_supports_skips_support_block():
    raw, rights = _clear_winner_scene()
    rep = sensitivity.ablation_report(raw, rights, native_posting_m=_L,
                                      reference_id="ref", target_support_m=_L)
    assert rep["support"] is None
    # overall_stable collapses to lens stability when no support ablation runs.
    assert rep["overall_stable"] is True
    assert rep["overall_stable"] == rep["lens"]["recommendation_stable"]


def test_report_is_deterministic():
    raw, rights = _clear_winner_scene()
    a = sensitivity.ablation_report(raw, rights, native_posting_m=_L,
                                    reference_id="ref", target_support_m=_L,
                                    supports=(10.0, 20.0))
    raw2, rights2 = _clear_winner_scene()
    b = sensitivity.ablation_report(raw2, rights2, native_posting_m=_L,
                                    reference_id="ref", target_support_m=_L,
                                    supports=(10.0, 20.0))
    assert a == b
