"""Tests for the terrain morphological fingerprint + similarity ranking.

Dependency-free, assert-based (no pytest), small fixed-seed synthetic
fixtures -- mirrors the plain ``def test_*()`` style of test_descriptors.py
and test_features.py: no network, known-answer or ordering assertions.
"""
import json

import numpy as np

from terratrace import (fingerprint, synthetic, spectral, anisotropy,
                        fractal, entropy_terrain, lacunarity)


def _rough(amplitude, seed, shape=(48, 48)):
    return synthetic.rough_field(shape, amplitude=amplitude, seed=seed)


def test_fingerprint_keys_floats_json_and_deterministic():
    z = (synthetic.plane((48, 48), slope_x=0.3, slope_y=0.1)
         + _rough(1.0, seed=5))
    fp = fingerprint.terrain_fingerprint(z)
    # exactly the documented field set, in FINGERPRINT_FIELDS order
    assert tuple(fp.keys()) == fingerprint.FINGERPRINT_FIELDS, tuple(fp.keys())
    assert set(fp) == set(fingerprint.FINGERPRINT_FIELDS)
    # every value is a plain float
    for k, v in fp.items():
        assert type(v) is float, (k, type(v))
    # this fixture is rough + tilted -> every descriptor is defined (finite)
    assert all(np.isfinite(v) for v in fp.values()), fp
    # JSON-serialisable and round-trips exactly (finite floats)
    dumped = json.dumps(fp)
    assert isinstance(dumped, str) and json.loads(dumped) == fp
    # deterministic: same array -> equal dict
    assert fingerprint.terrain_fingerprint(z) == fp


def test_similarity_of_identical_fingerprint_is_one():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.2)
         + _rough(1.5, seed=7))
    fp = fingerprint.terrain_fingerprint(z)
    assert fingerprint.similarity(fp, fp) == 1.0


def test_similarity_discriminates_plane_from_rough():
    # smooth flat plane vs a very rough field, and two draws of the SAME
    # rough process (same amplitude, different seed).
    plane = synthetic.plane((48, 48), slope_x=0.0, slope_y=0.0)
    rough_a = _rough(4.0, seed=101)
    rough_b = _rough(4.0, seed=202)
    fp_plane = fingerprint.terrain_fingerprint(plane)
    fp_a = fingerprint.terrain_fingerprint(rough_a)
    fp_b = fingerprint.terrain_fingerprint(rough_b)
    s_plane_rough = fingerprint.similarity(fp_plane, fp_a)
    s_same_process = fingerprint.similarity(fp_a, fp_b)
    assert s_plane_rough < s_same_process, (s_plane_rough, s_same_process)
    print("plane-vs-rough=%.6f  same-process=%.6f" % (s_plane_rough, s_same_process))


def test_rank_library_matches_same_process_first():
    base_hill = synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
    library = {
        "plane": synthetic.plane((48, 48), slope_x=0.05, slope_y=0.0),
        "moderate_hill": base_hill + _rough(0.8, seed=1),
        "rough": _rough(10.0, seed=2),
    }
    # a NEW draw of the moderate-hill process (same base hill, new noise seed)
    query = base_hill + _rough(0.8, seed=777)
    ranked = fingerprint.rank_library(query, library)
    assert ranked[0][0] == "moderate_hill", ranked
    # fully ordered descending, every library entry present exactly once
    sims = [s for _, s in ranked]
    assert sims == sorted(sims, reverse=True), sims
    assert {name for name, _ in ranked} == set(library)
    print("rank:", [(n, round(s, 4)) for n, s in ranked])


def test_fingerprint_vector_length_and_order():
    z = (synthetic.plane((48, 48), slope_x=0.1, slope_y=0.2)
         + _rough(1.0, seed=3))
    fp = fingerprint.terrain_fingerprint(z)
    vec = fingerprint.fingerprint_vector(fp)
    assert len(vec) == len(fingerprint.FINGERPRINT_FIELDS)
    assert all(type(x) is float for x in vec)
    # matches the dict order exactly
    assert vec == tuple(fp[name] for name in fingerprint.FINGERPRINT_FIELDS)
    # computing from the raw array yields the same vector as from the dict
    assert fingerprint.fingerprint_vector(z) == vec


def test_library_scales_and_scale_aware_ranking():
    base_hill = synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
    library = {
        "plane": synthetic.plane((48, 48), slope_x=0.05, slope_y=0.0),
        "moderate_hill": base_hill + _rough(0.8, seed=1),
        "rough": _rough(10.0, seed=2),
    }
    scales = fingerprint.library_scales(library)
    assert len(scales) == len(fingerprint.FINGERPRINT_FIELDS)
    assert all(type(s) is float and np.isfinite(s) and s > 0.0 for s in scales), scales
    # scale-aware ranking still puts the same-process entry first
    query = base_hill + _rough(0.8, seed=777)
    ranked = fingerprint.rank_library(query, library, scales=scales)
    assert ranked[0][0] == "moderate_hill", ranked


# --- opt-in landform component (geomorphon spectrum + TV similarity term) ----

def test_fingerprint_default_has_no_landform_key():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=9))
    fp = fingerprint.terrain_fingerprint(z)                 # include_landform=False
    assert fingerprint.LANDFORM_SPECTRUM_KEY not in fp
    assert tuple(fp.keys()) == fingerprint.FINGERPRINT_FIELDS


def test_fingerprint_include_landform_is_additive_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=9))
    base = fingerprint.terrain_fingerprint(z)               # no landform
    withlf = fingerprint.terrain_fingerprint(z, include_landform=True)
    # additive: every FINGERPRINT_FIELDS scalar is byte-identical to the default
    for field in fingerprint.FINGERPRINT_FIELDS:
        assert withlf[field] == base[field], field
    spec = withlf[fingerprint.LANDFORM_SPECTRUM_KEY]
    assert isinstance(spec, list) and len(spec) == 9
    assert all(isinstance(row, list) and len(row) == 9 for row in spec)
    assert all(type(v) is float for row in spec for v in row)
    # normalised spectrum of a non-degenerate surface sums to ~1
    assert abs(sum(v for row in spec for v in row) - 1.0) < 1e-9
    # the landform-bearing fingerprint still JSON round-trips exactly
    assert json.loads(json.dumps(withlf)) == withlf
    # deterministic
    assert fingerprint.terrain_fingerprint(z, include_landform=True) == withlf


def test_spectrum_tv_bounds_and_known_values():
    a = [[0.0] * 9 for _ in range(9)]
    b = [[0.0] * 9 for _ in range(9)]
    a[0][0] = 1.0                       # all mass in one (n_plus, n_minus) bin
    b[8][0] = 1.0                       # all mass in a different, disjoint bin
    assert fingerprint.spectrum_tv(a, a) == 0.0
    assert abs(fingerprint.spectrum_tv(a, b) - 1.0) < 1e-12
    # half-overlapping distributions -> tv = 0.5
    c = [[0.0] * 9 for _ in range(9)]
    c[0][0] = 0.5
    c[8][0] = 0.5
    assert abs(fingerprint.spectrum_tv(a, c) - 0.5) < 1e-12
    # symmetric and a plain float
    assert fingerprint.spectrum_tv(a, b) == fingerprint.spectrum_tv(b, a)
    assert type(fingerprint.spectrum_tv(a, c)) is float


def test_similarity_landform_term_active_and_opt_in_preserves_default():
    plane = synthetic.plane((48, 48), slope_x=0.1, slope_y=0.0)
    rough_a = _rough(5.0, seed=21)
    rough_b = _rough(5.0, seed=22)
    fp_plane = fingerprint.terrain_fingerprint(plane, include_landform=True)
    fp_a = fingerprint.terrain_fingerprint(rough_a, include_landform=True)
    fp_b = fingerprint.terrain_fingerprint(rough_b, include_landform=True)

    # identical signatures -> 1.0 even with the landform term switched on
    assert fingerprint.similarity(fp_a, fp_a, include_landform=True) == 1.0

    # same rough process is more similar than plane-vs-rough (landform-aware)
    s_same = fingerprint.similarity(fp_a, fp_b, include_landform=True)
    s_diff = fingerprint.similarity(fp_plane, fp_a, include_landform=True)
    assert s_diff < s_same, (s_diff, s_same)

    # the landform term is actually active: for a pair with differing spectra it
    # strictly lowers the similarity relative to morphology-only
    s_morph = fingerprint.similarity(fp_plane, fp_a, include_landform=False)
    assert fingerprint.similarity(fp_plane, fp_a, include_landform=True) < s_morph

    # opt-out is byte-identical to the pre-existing morphology-only similarity,
    # and the extra landform key never perturbs the morphology distance
    assert s_morph == fingerprint.similarity(fp_plane, fp_a)
    plane_def = fingerprint.terrain_fingerprint(plane)
    a_def = fingerprint.terrain_fingerprint(rough_a)
    assert fingerprint.similarity(fp_plane, fp_a) == \
        fingerprint.similarity(plane_def, a_def)


def test_rank_library_landform_optin_and_missing_spectrum_raises():
    base_hill = synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
    library = {
        "plane": synthetic.plane((48, 48), slope_x=0.05, slope_y=0.0),
        "moderate_hill": base_hill + _rough(0.8, seed=1),
        "rough": _rough(10.0, seed=2),
    }
    query = base_hill + _rough(0.8, seed=777)
    # landform-aware ranking over raw arrays (spectra computed on the fly)
    ranked = fingerprint.rank_library(query, library, include_landform=True)
    assert ranked[0][0] == "moderate_hill", ranked
    sims = [s for _, s in ranked]
    assert sims == sorted(sims, reverse=True), sims
    assert {name for name, _ in ranked} == set(library)

    # a dict fingerprint built WITHOUT the landform spectrum cannot opt in
    fp_no_landform = fingerprint.terrain_fingerprint(query)   # include_landform=False
    raised = False
    try:
        fingerprint.similarity(fp_no_landform, fp_no_landform, include_landform=True)
    except ValueError:
        raised = True
    assert raised, "expected ValueError for a fingerprint lacking a landform spectrum"


# --- opt-in scale/fabric component (spectral slope + band ratios + fabric) ---

def test_fingerprint_default_has_no_scale_fabric_key():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=9))
    fp = fingerprint.terrain_fingerprint(z)              # include_scale_fabric=False
    assert fingerprint.SCALE_FABRIC_KEY not in fp
    assert tuple(fp.keys()) == fingerprint.FINGERPRINT_FIELDS


def test_fingerprint_include_scale_fabric_is_additive_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=9))
    base = fingerprint.terrain_fingerprint(z)
    withsf = fingerprint.terrain_fingerprint(z, include_scale_fabric=True)
    # additive: every FINGERPRINT_FIELDS scalar is byte-identical to the default
    for field in fingerprint.FINGERPRINT_FIELDS:
        assert withsf[field] == base[field], field
    sf = withsf[fingerprint.SCALE_FABRIC_KEY]
    assert set(sf) == set(fingerprint.SCALE_FABRIC_FIELDS), set(sf)
    assert all(type(v) is float for v in sf.values()), sf
    # the three band ratios form a scale-free wavelength shape summing to ~1
    ratios = (sf["rough_long_ratio"] + sf["rough_mid_ratio"]
              + sf["rough_short_ratio"])
    assert abs(ratios - 1.0) < 1e-9, ratios
    # JSON round-trips exactly and the build is deterministic
    assert json.loads(json.dumps(withsf)) == withsf
    assert fingerprint.terrain_fingerprint(z, include_scale_fabric=True) == withsf


def test_fingerprint_scale_fabric_matches_source_signatures():
    z = (synthetic.plane((48, 48), slope_x=0.1, slope_y=0.2) + _rough(1.5, seed=12))
    sf = fingerprint.terrain_fingerprint(z, include_scale_fabric=True)[
        fingerprint.SCALE_FABRIC_KEY]
    spec = spectral.spectral_signature(z)
    aniso = anisotropy.anisotropy_signature(z)
    assert np.isfinite(sf["spectral_slope"]) and np.isfinite(sf["anisotropy_strength"])
    assert sf["spectral_slope"] == float(spec["spectral_slope"])
    assert sf["anisotropy_strength"] == float(aniso["strength"])
    total = spec["rough_long"] + spec["rough_mid"] + spec["rough_short"]
    assert abs(sf["rough_long_ratio"] - spec["rough_long"] / total) < 1e-12


def test_scale_fabric_distance_bounds_symmetry_and_known_values():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=14))
    sf = fingerprint.terrain_fingerprint(z, include_scale_fabric=True)[
        fingerprint.SCALE_FABRIC_KEY]
    other = fingerprint.terrain_fingerprint(_rough(6.0, seed=15),
                                            include_scale_fabric=True)[
        fingerprint.SCALE_FABRIC_KEY]
    # identical -> 0.0; general pair -> bounded [0,1], symmetric, plain float
    assert fingerprint.scale_fabric_distance(sf, sf) == 0.0
    d = fingerprint.scale_fabric_distance(sf, other)
    assert type(d) is float and 0.0 <= d <= 1.0, d
    assert fingerprint.scale_fabric_distance(sf, other) == \
        fingerprint.scale_fabric_distance(other, sf)
    # a hand-built pair maximally separated on every axis -> distance 1.0
    a = {"spectral_slope": 0.0, "rough_long_ratio": 1.0, "rough_mid_ratio": 0.0,
         "rough_short_ratio": 0.0, "anisotropy_strength": 0.0}
    b = {"spectral_slope": fingerprint.SCALE_FABRIC_SLOPE_SPAN,
         "rough_long_ratio": 0.0, "rough_mid_ratio": 0.0, "rough_short_ratio": 1.0,
         "anisotropy_strength": 1.0}
    assert abs(fingerprint.scale_fabric_distance(a, b) - 1.0) < 1e-12
    # all-NaN components -> 0.0 (no information, no penalty), kept finite
    nan5 = {k: float("nan") for k in fingerprint.SCALE_FABRIC_FIELDS}
    assert fingerprint.scale_fabric_distance(nan5, nan5) == 0.0


def test_similarity_scale_fabric_term_active_and_opt_in_preserves_default():
    smooth = (synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
              + _rough(0.3, seed=41))
    rough_a = _rough(5.0, seed=21)
    rough_b = _rough(5.0, seed=22)
    fp_s = fingerprint.terrain_fingerprint(smooth, include_scale_fabric=True)
    fp_a = fingerprint.terrain_fingerprint(rough_a, include_scale_fabric=True)
    fp_b = fingerprint.terrain_fingerprint(rough_b, include_scale_fabric=True)

    # identical signatures -> 1.0 even with the scale/fabric term switched on
    assert fingerprint.similarity(fp_a, fp_a, include_scale_fabric=True) == 1.0

    # same rough process more similar than smooth-vs-rough (scale/fabric-aware)
    s_same = fingerprint.similarity(fp_a, fp_b, include_scale_fabric=True)
    s_diff = fingerprint.similarity(fp_s, fp_a, include_scale_fabric=True)
    assert s_diff < s_same, (s_diff, s_same)

    # the term is actually active: for a pair with differing scale/fabric it
    # strictly lowers similarity relative to morphology-only
    s_morph = fingerprint.similarity(fp_s, fp_a, include_scale_fabric=False)
    assert fingerprint.similarity(fp_s, fp_a, include_scale_fabric=True) < s_morph

    # opt-out is byte-identical to the pre-existing morphology-only similarity,
    # and the extra scale/fabric key never perturbs the morphology distance
    assert s_morph == fingerprint.similarity(fp_s, fp_a)
    s_def = fingerprint.terrain_fingerprint(smooth)
    a_def = fingerprint.terrain_fingerprint(rough_a)
    assert fingerprint.similarity(fp_s, fp_a) == \
        fingerprint.similarity(s_def, a_def)


def test_rank_library_scale_fabric_optin_and_missing_raises():
    base_hill = synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
    library = {
        "plane": synthetic.plane((48, 48), slope_x=0.05, slope_y=0.0),
        "moderate_hill": base_hill + _rough(0.8, seed=1),
        "rough": _rough(10.0, seed=2),
    }
    query = base_hill + _rough(0.8, seed=777)
    # scale/fabric-aware ranking over raw arrays (signatures computed on the fly)
    ranked = fingerprint.rank_library(query, library, include_scale_fabric=True)
    assert ranked[0][0] == "moderate_hill", ranked
    sims = [s for _, s in ranked]
    assert sims == sorted(sims, reverse=True), sims
    assert {name for name, _ in ranked} == set(library)

    # a dict fingerprint built WITHOUT the scale/fabric block cannot opt in
    fp_no_sf = fingerprint.terrain_fingerprint(query)   # include_scale_fabric=False
    raised = False
    try:
        fingerprint.similarity(fp_no_sf, fp_no_sf, include_scale_fabric=True)
    except ValueError:
        raised = True
    assert raised, "expected ValueError for a fingerprint lacking a scale/fabric block"


# --- opt-in texture battery (spectral slope + fractal dim + entropy + lacunarity)

def test_fingerprint_default_has_no_texture_key():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=9))
    fp = fingerprint.terrain_fingerprint(z)              # include_texture=False
    assert fingerprint.TEXTURE_KEY not in fp
    assert tuple(fp.keys()) == fingerprint.FINGERPRINT_FIELDS


def test_fingerprint_include_texture_is_additive_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=9))
    base = fingerprint.terrain_fingerprint(z)
    withtx = fingerprint.terrain_fingerprint(z, include_texture=True)
    # additive: every FINGERPRINT_FIELDS scalar is byte-identical to the default
    for field in fingerprint.FINGERPRINT_FIELDS:
        assert withtx[field] == base[field], field
    tx = withtx[fingerprint.TEXTURE_KEY]
    # exactly the 4 documented texture fields, every value a plain float
    assert set(tx) == set(fingerprint.TEXTURE_FIELDS), set(tx)
    assert all(type(v) is float for v in tx.values()), tx
    # this rough + tilted fixture leaves every texture scalar defined (finite)
    assert all(np.isfinite(v) for v in tx.values()), tx
    # JSON round-trips exactly and the build is deterministic
    assert json.loads(json.dumps(withtx)) == withtx
    assert fingerprint.terrain_fingerprint(z, include_texture=True) == withtx


def test_fingerprint_texture_matches_source_signatures():
    z = (synthetic.plane((48, 48), slope_x=0.1, slope_y=0.2) + _rough(1.5, seed=12))
    tx = fingerprint.terrain_fingerprint(z, include_texture=True)[
        fingerprint.TEXTURE_KEY]
    # each stored scalar equals a direct call to its source module (default dx=1)
    assert tx["spectral_slope"] == float(
        spectral.spectral_signature(z)["spectral_slope"])
    assert tx["fractal_dim"] == float(fractal.box_counting_dimension(z))
    assert tx["slope_entropy_norm"] == float(
        entropy_terrain.entropy_signature(z)["slope_entropy_norm"])
    assert tx["lacunarity_r2"] == float(
        lacunarity.lacunarity_signature(z)["lacunarity_r2"])
    # fractal dimension lives in its documented [2, 3] band; entropy in [0, 1]
    assert 2.0 <= tx["fractal_dim"] <= 3.0, tx["fractal_dim"]
    assert 0.0 <= tx["slope_entropy_norm"] <= 1.0, tx["slope_entropy_norm"]


def test_texture_distance_bounds_symmetry_and_known_values():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1) + _rough(2.0, seed=14))
    tx = fingerprint.terrain_fingerprint(z, include_texture=True)[
        fingerprint.TEXTURE_KEY]
    other = fingerprint.terrain_fingerprint(_rough(6.0, seed=15),
                                            include_texture=True)[
        fingerprint.TEXTURE_KEY]
    # identical -> 0.0; general pair -> bounded [0,1], symmetric, plain float
    assert fingerprint.texture_distance(tx, tx) == 0.0
    d = fingerprint.texture_distance(tx, other)
    assert type(d) is float and 0.0 <= d <= 1.0, d
    assert fingerprint.texture_distance(tx, other) == \
        fingerprint.texture_distance(other, tx)
    # a hand-built pair maximally separated on every axis (each a full span) -> 1.0
    a = {"spectral_slope": 0.0, "fractal_dim": 2.0,
         "slope_entropy_norm": 0.0, "lacunarity_r2": 1.0}
    b = {"spectral_slope": fingerprint.TEXTURE_SPANS["spectral_slope"],
         "fractal_dim": 3.0, "slope_entropy_norm": 1.0, "lacunarity_r2": 2.0}
    assert abs(fingerprint.texture_distance(a, b) - 1.0) < 1e-12
    # all-NaN components -> 0.0 (no information, no penalty), kept finite
    nan4 = {k: float("nan") for k in fingerprint.TEXTURE_FIELDS}
    assert fingerprint.texture_distance(nan4, nan4) == 0.0


def test_similarity_texture_term_active_and_opt_in_preserves_default():
    smooth = (synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
              + _rough(0.3, seed=41))
    rough_a = _rough(5.0, seed=21)
    rough_b = _rough(5.0, seed=22)
    fp_s = fingerprint.terrain_fingerprint(smooth, include_texture=True)
    fp_a = fingerprint.terrain_fingerprint(rough_a, include_texture=True)
    fp_b = fingerprint.terrain_fingerprint(rough_b, include_texture=True)

    # identical signatures -> 1.0 even with the texture term switched on
    assert fingerprint.similarity(fp_a, fp_a, include_texture=True) == 1.0

    # a valid, bounded similarity in (0, 1] with the texture term active
    s_diff = fingerprint.similarity(fp_s, fp_a, include_texture=True)
    assert type(s_diff) is float and 0.0 < s_diff <= 1.0, s_diff

    # a terrain is more texture-similar to ITSELF than to a very different one
    assert fingerprint.similarity(fp_a, fp_a, include_texture=True) > s_diff

    # same rough process more similar than smooth-vs-rough (texture-aware)
    s_same = fingerprint.similarity(fp_a, fp_b, include_texture=True)
    assert s_diff < s_same, (s_diff, s_same)

    # the term is actually active: for a pair with differing texture it strictly
    # lowers similarity relative to morphology-only
    s_morph = fingerprint.similarity(fp_s, fp_a, include_texture=False)
    assert fingerprint.similarity(fp_s, fp_a, include_texture=True) < s_morph

    # opt-out is byte-identical to the pre-existing morphology-only similarity,
    # and the extra texture key never perturbs the morphology distance
    assert s_morph == fingerprint.similarity(fp_s, fp_a)
    s_def = fingerprint.terrain_fingerprint(smooth)
    a_def = fingerprint.terrain_fingerprint(rough_a)
    assert fingerprint.similarity(fp_s, fp_a) == \
        fingerprint.similarity(s_def, a_def)


def test_rank_library_texture_optin_and_missing_raises():
    base_hill = synthetic.gaussian_hill((48, 48), amplitude=12.0, sigma=12.0)
    library = {
        "plane": synthetic.plane((48, 48), slope_x=0.05, slope_y=0.0),
        "moderate_hill": base_hill + _rough(0.8, seed=1),
        "rough": _rough(10.0, seed=2),
    }
    query = base_hill + _rough(0.8, seed=777)
    # texture-aware ranking over raw arrays (signatures computed on the fly)
    ranked = fingerprint.rank_library(query, library, include_texture=True)
    assert ranked[0][0] == "moderate_hill", ranked
    sims = [s for _, s in ranked]
    assert sims == sorted(sims, reverse=True), sims
    assert {name for name, _ in ranked} == set(library)

    # a dict fingerprint built WITHOUT the texture block cannot opt in
    fp_no_tx = fingerprint.terrain_fingerprint(query)   # include_texture=False
    raised = False
    try:
        fingerprint.similarity(fp_no_tx, fp_no_tx, include_texture=True)
    except ValueError:
        raised = True
    assert raised, "expected ValueError for a fingerprint lacking a texture block"
