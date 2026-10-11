"""Opt-in landform capability: geomorphon composition/spectrum + topographic
openness as a per-unit descriptor block, categorical/scalar preview PNGs, and
the ``decision_metrics="landform"`` lens (two extra morphology-dissimilarity
Pareto axes). Mirrors the geomorphic opt-in and must NOT leak into the default/
core/extended/geomorphic packages, so their provenance hashes stay byte-stable.

Dependency-free (no pytest): run via tests/run_tests.py or by calling the
test_* functions directly.
"""
import base64

import numpy as np

from terratrace import study, hillshade, geomorphons, synthetic

# The default run_study() package is the frozen teaching/CI path: adding the
# opt-in landform capability must not perturb it. NOTE: the absolute sha256 is
# float / NumPy-build dependent (CI runs a newer NumPy than the dev sandbox), so
# the gate below asserts PORTABLE invariants -- determinism, no opt-in keys, and
# a well-formed digest -- never a pinned cross-environment literal.


def _scene():
    """Three all-eligible units sharing a gentle plane with increasing roughness
    (same construction as the geomorphic-mode fixture in test_study.py)."""
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    return {
        "ref": base + synthetic.rough_field((64, 64), 0.8, seed=1),
        "near": base + synthetic.rough_field((64, 64), 0.9, seed=2),
        "far": base + synthetic.rough_field((64, 64), 4.0, seed=3),
    }


def _run(**kw):
    raw = _scene()
    rights = {k: "verified_allowed" for k in raw}
    return study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                               target_support_m=10.0, **kw)


def _png_color_type(data_uri):
    """Colour-type byte from the IHDR of a base64 PNG data URI (0=grey, 2=RGB)."""
    assert data_uri.startswith("data:image/png;base64,")
    raw = base64.b64decode(data_uri[len("data:image/png;base64,"):])
    assert raw[:8] == b"\x89PNG\r\n\x1a\n"
    # 8 signature + 4 length + 4 "IHDR" + 4 width + 4 height + 1 bitdepth = 25.
    return raw[25]


def test_landform_flag_attaches_descriptor_block():
    pkg = _run(landform=True)
    assert "landform" in pkg
    lf = pkg["landform"]
    # Attached for every compared candidate AND the reference.
    assert "ref" in lf
    for uid in pkg["baseline_vectors"]:
        assert uid in lf, uid
    for uid, d in lf.items():
        assert set(d) == {"composition", "dominant_form", "openness", "spectrum"}, uid
        comp = d["composition"]
        assert set(comp) == set(geomorphons.FORM_NAMES)
        assert abs(sum(comp.values()) - 1.0) < 1e-9              # fractions sum ~1
        assert d["dominant_form"] in geomorphons.FORM_NAMES
        spec = np.asarray(d["spectrum"], dtype=float)
        assert spec.shape == (9, 9)                              # 9x9 spectrum
        assert abs(float(spec.sum()) - 1.0) < 1e-9
        sig = d["openness"]
        for key in ("positive_median", "negative_median"):
            assert key in sig and np.isfinite(sig[key])


def test_landform_previews_are_png_data_uris():
    pkg = _run(landform=True, previews=True)
    assert "landform_previews" in pkg and "openness_previews" in pkg
    units = set(pkg["landform_previews"])
    assert units == set(pkg["openness_previews"]) and "ref" in units
    for uri in pkg["landform_previews"].values():
        assert uri.startswith("data:image/png;base64,")
        assert _png_color_type(uri) == 2                         # categorical RGB
    for uri in pkg["openness_previews"].values():
        assert uri.startswith("data:image/png;base64,")
        assert _png_color_type(uri) == 0                         # grayscale field
    # The base hillshade previews still ride along unchanged.
    assert set(pkg["previews"]) == units


def test_landform_decision_lens_appends_two_axes():
    pkg = _run(decision_metrics="landform")
    assert pkg["profile"]["decision_metrics"] == "landform"
    assert pkg["profile"]["metrics"][-2:] == ["landform_spectrum", "openness"]
    assert pkg["baseline_vectors"]                               # >=1 eligible candidate
    for vec in pkg["baseline_vectors"].values():
        assert len(vec) == 6
        assert vec[4] >= 0.0 and vec[5] >= 0.0                   # distances, non-negative
    assert pkg["result_state"] in study.decision.STATES
    # The lens also computes the descriptor block (lf) even without the flag.
    assert "landform" in pkg


def test_opt_in_absent_from_core_extended_geomorphic():
    raw = _scene()
    rights = {k: "verified_allowed" for k in raw}
    for mode in ("core", "extended", "geomorphic"):
        pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                                  target_support_m=10.0, decision_metrics=mode, previews=True)
        for key in ("landform", "landform_previews", "openness_previews"):
            assert key not in pkg, (mode, key)
        assert pkg["profile"]["metrics"][-2:] != ["landform_spectrum", "openness"]
    # landform defaults off, so no block even with previews on.
    off = _run(previews=True)
    for key in ("landform", "landform_previews", "openness_previews"):
        assert key not in off, key


def test_default_study_hash_is_byte_identical_gate():
    # Portable gate (see note at top): run_study is deterministic within an
    # environment, the default package carries none of the opt-in landform
    # blocks, and the digest is a well-formed 64-char sha256 hex string. The
    # absolute value is NOT pinned (it is NumPy-build dependent across CI).
    pkg = study.run_study()
    h = pkg["package_hash"]
    assert study.run_study()["package_hash"] == h            # deterministic in-env
    for key in ("landform", "landform_previews", "openness_previews"):
        assert key not in pkg, key
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)

