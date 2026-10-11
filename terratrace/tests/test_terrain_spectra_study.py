"""Opt-in, GATED per-unit terrain-spectra descriptor block: a radially-averaged
PSD roughness signature (spectral.py) + a directional-fabric anisotropy signature
(anisotropy.py), attached per compared/eligible unit. Mirrors the geomorphic/
landform opt-in blocks and must NOT leak into the default/core/extended/
geomorphic/landform packages, so their provenance hashes stay byte-stable.

Map-scale MORPHOLOGY / roughness-spectrum + directional-fabric descriptors only --
no traversability, hazard, geologic, or mission claim.

Dependency-free (no pytest): run via tests/run_tests.py or by calling the
test_* functions directly.
"""
from terratrace import study, synthetic

# The absolute sha256 of run_study() is float / NumPy-build dependent (CI runs a
# newer NumPy than the dev sandbox), so the gate below asserts PORTABLE invariants
# -- determinism in-env, no opt-in keys, a well-formed digest -- and NEVER a pinned
# cross-environment hash literal (pinning a literal broke CI twice).

SPECTRAL_KEYS = {"spectral_slope", "total_power", "roughness_rms",
                 "peak_wavelength_m", "rough_long", "rough_mid", "rough_short"}
ANISOTROPY_KEYS = {"strength", "orientation_deg", "isotropy", "mean_roughness"}


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


def test_terrain_spectra_flag_attaches_spectral_and_anisotropy():
    pkg = _run(terrain_spectra=True)
    assert "spectral" in pkg and "anisotropy" in pkg
    spec, aniso = pkg["spectral"], pkg["anisotropy"]
    # Same key set for both blocks, covering every compared candidate AND the
    # reference (all three fixture units are eligible/compared).
    assert set(spec) == set(aniso)
    assert "ref" in spec and "ref" in aniso
    for uid in pkg["baseline_vectors"]:
        assert uid in spec and uid in aniso, uid
    # Each entry is a dict of exactly the documented float descriptors.
    for uid, d in spec.items():
        assert set(d) == SPECTRAL_KEYS, uid
        for k, v in d.items():
            assert isinstance(v, float), (uid, k)
    for uid, d in aniso.items():
        assert set(d) == ANISOTROPY_KEYS, uid
        for k, v in d.items():
            assert isinstance(v, float), (uid, k)


def test_terrain_spectra_off_by_default_carries_neither_key():
    # Explicit flag off.
    off = _run(terrain_spectra=False)
    assert "spectral" not in off and "anisotropy" not in off
    # Flag absent (the default) behaves identically.
    default = _run()
    assert "spectral" not in default and "anisotropy" not in default
    # And the default synthetic study path carries neither key.
    pkg = study.run_study()
    assert "spectral" not in pkg and "anisotropy" not in pkg


def test_terrain_spectra_does_not_leak_into_other_modes():
    raw = _scene()
    rights = {k: "verified_allowed" for k in raw}
    for mode in ("core", "extended", "geomorphic", "landform"):
        pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                                  target_support_m=10.0, decision_metrics=mode)
        assert "spectral" not in pkg and "anisotropy" not in pkg, mode
    # Even alongside the landform descriptor flag the keys stay absent unless
    # terrain_spectra is explicitly requested.
    lf = _run(landform=True)
    assert "spectral" not in lf and "anisotropy" not in lf


def test_default_study_hash_is_portable_gate():
    # Portable gate (see note at top): run_study is deterministic within an
    # environment, the default package carries neither terrain-spectra block, and
    # the digest is a well-formed 64-char sha256 hex string. The absolute value is
    # NOT pinned (it is NumPy-build dependent across CI).
    pkg = study.run_study()
    h = pkg["package_hash"]
    assert study.run_study()["package_hash"] == h            # deterministic in-env
    for key in ("spectral", "anisotropy"):
        assert key not in pkg, key
    assert len(h) == 64 and all(c in "0123456789abcdef" for c in h)
