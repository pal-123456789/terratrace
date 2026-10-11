"""Sixth decision lens: ``decision_metrics="hydro"``.

The opt-in hydro lens appends three per-unit hydro-geometric scalars - mean
Topographic Wetness Index, mean aspect-field convergence, and peak
flow-accumulation dissection - as extra Pareto axes, so the hydro descriptors
actually drive the analog decision (not just the analysis bank). It mirrors the
geomorphic/landform/texture lenses exactly: the axes/metrics appear ONLY in
hydro mode, so the core/extended/geomorphic/landform/texture packages (and the
gated run_study package hash) are untouched.

These tests exercise the lens through the real engine with PORTABLE invariants
only - the gated-build hash invariant is checked separately by the pinned HASH
guard command, so no package_hash literal lives in this file.
"""
import numpy as np

from terratrace import study, synthetic

HYDRO_METRICS = ["twi_mean", "convergence_mean", "dissection"]


def _hydro_scene():
    """A 3-unit scene: a smooth reference, a near-duplicate ``match`` whose hydro
    scalars track the reference, and a channelized/convergent ``diff`` with clearly
    different TWI / convergence / dissection (a V-shaped valley vs a gentle tilt)."""
    shp = (64, 64)
    ref = synthetic.plane(shp, slope_x=0.02, dx=10.0) + synthetic.rough_field(shp, 0.8, seed=1)
    match = ref + synthetic.rough_field(shp, 0.06, seed=7)
    valley = np.tile(0.03 * np.abs(np.arange(shp[1]) - 31.5) * 10.0, (shp[0], 1))
    diff = valley + synthetic.rough_field(shp, 1.2, seed=3)
    return {"ref": ref, "match": match, "diff": diff}


def test_hydro_mode_adds_three_scalar_axes():
    raw = _hydro_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="hydro")
    assert pkg["profile"]["decision_metrics"] == "hydro"
    # The three hydro scalars are the trailing Pareto axes, in this exact order.
    assert pkg["profile"]["metrics"][-3:] == HYDRO_METRICS
    assert len(pkg["profile"]["metrics"]) == 7
    # Core 4 + 3 hydro axes = length-7 vectors for every eligible candidate.
    assert pkg["baseline_vectors"], "expected eligible candidates"
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 7
    # Valid package: allowed decision state, a frontier over the 7-axis vectors,
    # and the reference present.
    assert pkg["result_state"] in study.decision.STATES
    assert "frontier" in pkg and pkg["frontier"]["rank"]
    assert "ref" in pkg["unit_metadata"]


def test_reference_own_hydro_axes_are_zero():
    # Same 0.0-vs-self convention as the connectivity-scalar / texture lenses: the
    # candidate->reference distance of the reference against itself is exactly 0.0
    # on each of the three hydro axes.
    hyd = {
        "ref": {"twi_mean": 6.08, "convergence_mean": -0.01, "dissection": 0.27},
        "cand": {"twi_mean": 5.62, "convergence_mean": -0.23, "dissection": 0.46},
    }
    assert study._hydro_dims(hyd, "ref", "ref") == (0.0, 0.0, 0.0)
    # A non-identical candidate is non-zero on at least one axis (axes are live).
    assert any(d > 0 for d in study._hydro_dims(hyd, "cand", "ref"))


def test_hydro_axes_drive_the_decision():
    raw = _hydro_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="hydro")
    # The hydro-similar near-duplicate is favored over the hydro-dissimilar
    # channelized candidate: Pareto non-dominated, dominates it, and is recommended.
    assert pkg["recommended_unit"] == "match"
    assert pkg["frontier"]["rank"]["match"] == 1
    assert pkg["frontier"]["rank"]["diff"] > 1
    assert pkg["frontier"]["dominance_matrix"]["diff|match"] == "match"
    # The three trailing axes ARE the hydro axes and they genuinely separate the
    # two candidates in match's favour (each strictly smaller for match) - the hydro
    # scalars, not just the core four, carry the decision.
    mv, dv = pkg["baseline_vectors"]["match"], pkg["baseline_vectors"]["diff"]
    assert all(m < d for m, d in zip(mv[-3:], dv[-3:]))
    # And the surfaces really are hydro-distinct: the channelized 'diff' is far more
    # convergent AND more dissected than the smooth reference, while 'match' tracks it.
    s_ref = study._hydro_scalars(raw["ref"], 10.0)
    s_match = study._hydro_scalars(raw["match"], 10.0)
    s_diff = study._hydro_scalars(raw["diff"], 10.0)
    for key in ("convergence_mean", "dissection"):
        assert abs(s_diff[key] - s_ref[key]) > abs(s_match[key] - s_ref[key])


def test_core_mode_has_length_four_vectors_without_hydro_names():
    raw = _hydro_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="core")
    assert pkg["profile"]["decision_metrics"] == "core"
    assert pkg["baseline_vectors"], "expected eligible candidates"
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 4
    # None of the hydro metric names leak into the core package.
    assert not any(m in pkg["profile"]["metrics"] for m in HYDRO_METRICS)


def test_hydro_axes_do_not_leak_into_other_modes():
    # The lens is gated: the trailing axes/metrics appear only in hydro mode, so the
    # core/extended/geomorphic/landform/texture packages stay byte-stable.
    raw = _hydro_scene()
    rights = {k: "verified_allowed" for k in raw}
    for mode in ("core", "extended", "geomorphic", "landform", "texture"):
        pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                                  target_support_m=10.0, decision_metrics=mode)
        assert pkg["profile"]["metrics"][-3:] != HYDRO_METRICS
        assert not any(m in pkg["profile"]["metrics"] for m in HYDRO_METRICS)
        assert "hydro" not in pkg


def test_default_study_is_gated_and_portable():
    # PORTABLE invariants only - no package_hash literal is pinned in this file.
    a = study.run_study()
    b = study.run_study()
    assert a["package_hash"] == b["package_hash"]            # deterministic
    assert "hydro" not in a                                   # lens is fully opt-in
    h = a["package_hash"]
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)  # 64-hex digest


def test_hydro_package_is_deterministic():
    raw = _hydro_scene()
    rights = {k: "verified_allowed" for k in raw}
    kw = dict(native_posting_m=10.0, reference_id="ref", target_support_m=10.0,
              decision_metrics="hydro")
    assert (study.compare_units(raw, rights, **kw)["package_hash"]
            == study.compare_units(raw, rights, **kw)["package_hash"])
