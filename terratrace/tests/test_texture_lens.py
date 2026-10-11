"""Fifth decision lens: ``decision_metrics="texture"``.

The opt-in texture lens appends three per-unit texture scalars - spectral slope,
box-counting fractal dimension, and surface-normal dispersion roughness - as
extra Pareto axes, so the texture descriptors actually drive the analog decision
(not just the analysis bank). It mirrors the geomorphic/landform lenses exactly:
the axes/metrics appear ONLY in texture mode, so the core/extended/geomorphic/
landform packages (and the gated run_study package hash) are untouched.

These tests exercise the lens through the real engine. The gated-build hash
invariant is checked separately by the pinned HASH guard command (so no
package_hash literal lives in this file).
"""
from terratrace import study

TEXTURE_METRICS = ["spectral_slope", "fractal_dim", "normal_roughness"]


def _texture_scene():
    """A 3-unit scene mirroring test_study.py's _geomorphic_scene: one reference
    plus a near (slightly rougher) and a far (much rougher) candidate."""
    from terratrace import synthetic
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    return {
        "ref": base + synthetic.rough_field((64, 64), 0.8, seed=1),
        "near": base + synthetic.rough_field((64, 64), 0.9, seed=2),
        "far": base + synthetic.rough_field((64, 64), 4.0, seed=3),
    }


def test_texture_mode_adds_three_scalar_axes():
    raw = _texture_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="texture")
    assert pkg["profile"]["decision_metrics"] == "texture"
    # The three texture scalars are the trailing Pareto axes, in this exact order.
    assert pkg["profile"]["metrics"][-3:] == TEXTURE_METRICS
    assert len(pkg["profile"]["metrics"]) == 7
    # Core 4 + 3 texture axes = length-7 vectors for every eligible candidate.
    assert pkg["baseline_vectors"], "expected eligible candidates"
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 7
    # The decision machinery is identical to the other lenses.
    assert pkg["result_state"] in study.decision.STATES


def test_reference_own_texture_axes_are_zero():
    # Same 0.0-vs-self convention as the connectivity-scalar / geomorphic /
    # landform lenses: the candidate->reference distance of the reference against
    # itself is exactly 0.0 on each of the three texture axes.
    tex = {
        "ref": {"spectral_slope": -2.31, "fractal_dim": 2.42, "normal_roughness": 0.17},
        "cand": {"spectral_slope": -1.10, "fractal_dim": 2.65, "normal_roughness": 0.33},
    }
    assert study._texture_dims(tex, "ref", "ref") == (0.0, 0.0, 0.0)
    # A non-identical candidate is non-zero on at least one axis (axes are live).
    assert any(d > 0 for d in study._texture_dims(tex, "cand", "ref"))


def test_core_mode_has_length_four_vectors_without_texture_names():
    raw = _texture_scene()
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, decision_metrics="core")
    assert pkg["profile"]["decision_metrics"] == "core"
    assert pkg["baseline_vectors"], "expected eligible candidates"
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 4
    # None of the texture metric names leak into the core package.
    assert not any(m in pkg["profile"]["metrics"] for m in TEXTURE_METRICS)


def test_texture_axes_do_not_leak_into_other_modes():
    # The lens is gated: the trailing axes/metrics appear only in texture mode, so
    # the core/extended/geomorphic/landform packages stay byte-stable.
    raw = _texture_scene()
    rights = {k: "verified_allowed" for k in raw}
    for mode in ("core", "extended", "geomorphic", "landform"):
        pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                                  target_support_m=10.0, decision_metrics=mode)
        assert pkg["profile"]["metrics"][-3:] != TEXTURE_METRICS
        assert not any(m in pkg["profile"]["metrics"] for m in TEXTURE_METRICS)
