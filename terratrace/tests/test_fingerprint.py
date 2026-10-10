"""Tests for the terrain morphological fingerprint + similarity ranking.

Dependency-free, assert-based (no pytest), small fixed-seed synthetic
fixtures -- mirrors the plain ``def test_*()`` style of test_descriptors.py
and test_features.py: no network, known-answer or ordering assertions.
"""
import json

import numpy as np

from terratrace import fingerprint, synthetic


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
