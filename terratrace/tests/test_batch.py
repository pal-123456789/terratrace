"""Cross-reference, multi-lens batch-study fixtures (synthetic, offline)."""
import json

import numpy as np

from terratrace import batch, synthetic


def _units(n=56, L=10.0):
    base = synthetic.plane((n, n), slope_x=0.02, dx=L)
    return {
        "mars_a": base + synthetic.rough_field((n, n), 0.8, seed=1),
        "mars_b": synthetic.plane((n, n), slope_x=0.025, dx=L) + synthetic.rough_field((n, n), 0.85, seed=11),
        "twin": base + synthetic.rough_field((n, n), 0.85, seed=2),
        "rough": base + synthetic.rough_field((n, n), 4.0, seed=3),
        "steep": synthetic.plane((n, n), slope_x=0.2, dx=L) + synthetic.rough_field((n, n), 0.9, seed=4),
    }


_REFS = ["mars_a", "mars_b"]
_CANDS = ["twin", "rough", "steep"]
_L = 10.0


def _run():
    return batch.run_batch(_units(), _REFS, _CANDS, _L, target_support_m=_L)


def test_batch_grid_shape_and_keys():
    rep = _run()
    assert rep["n_cells"] == len(_REFS) * 3          # 3 default decision modes
    assert len(rep["cells"]) == rep["n_cells"]
    for key in ("per_candidate", "consensus_shortlist", "robust_ordering",
                "decision_modes", "package_hash", "note"):
        assert key in rep, key
    assert set(rep["per_candidate"]) == set(_CANDS)


def test_batch_consensus_picks_the_true_analog():
    rep = _run()
    # The same-statistics twin is non-dominated in EVERY (reference x mode) cell,
    # so it is the sole consensus analog and ranks first.
    assert rep["consensus_shortlist"] == ["twin"]
    assert rep["robust_ordering"][0] == "twin"
    assert rep["per_candidate"]["twin"]["layer1_frequency"] == 1.0
    # The far-rougher candidate is never non-dominated; the far-steeper one may be
    # non-dominated under some lenses (not worse on every axis) but is NOT a
    # consensus analog -- exactly the nuance the batch synthesis is meant to show.
    assert rep["per_candidate"]["rough"]["layer1_frequency"] == 0.0
    assert rep["per_candidate"]["steep"]["layer1_frequency"] < 1.0
    assert "steep" not in rep["consensus_shortlist"] and "rough" not in rep["consensus_shortlist"]
    # Only the twin is ever the sole recommendation; under some lenses the honest
    # verdict is a TIE (no sole winner), so recommended_frequency sits in (0, 1].
    assert 0.0 < rep["per_candidate"]["twin"]["recommended_frequency"] <= 1.0
    assert rep["per_candidate"]["rough"]["recommended_frequency"] == 0.0
    assert rep["per_candidate"]["steep"]["recommended_frequency"] == 0.0


def test_batch_is_deterministic_and_json_serialisable():
    a, b = _run(), _run()
    assert a["package_hash"] == b["package_hash"]
    assert json.loads(json.dumps(a)) == a


def test_batch_respects_mode_subset():
    rep = batch.run_batch(_units(), _REFS, _CANDS, _L, target_support_m=_L,
                          decision_modes=("core",))
    assert rep["decision_modes"] == ["core"]
    assert rep["n_cells"] == len(_REFS)              # 2 refs x 1 mode
    assert rep["consensus_shortlist"] == ["twin"]


def test_batch_requires_references_and_candidates():
    u = _units()
    for refs, cands in (([], _CANDS), (_REFS, [])):
        try:
            batch.run_batch(u, refs, cands, _L)
            raised = False
        except ValueError:
            raised = True
        assert raised


def test_batch_per_candidate_fields_are_finite_floats():
    rep = _run()
    for c in _CANDS:
        pc = rep["per_candidate"][c]
        assert 0.0 <= pc["layer1_frequency"] <= 1.0
        assert 0.0 <= pc["recommended_frequency"] <= 1.0
        assert isinstance(pc["cells_ranked"], int)
        assert np.isfinite(pc["mean_layer"])
