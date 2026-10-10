"""Tests for the rule-based terrain-type classifier (dependency-free, assert-based).

Mirrors the plain ``def test_*()`` style of test_descriptors.py: no pytest, no
network, small deterministic synthetic fixtures with intuitive expected types.
"""
import numpy as np

from terratrace import terrain_classify, synthetic, descriptors

SHAPE = (56, 56)
RESULT_KEYS = {"type", "confidence", "evidence", "scores"}


def _near_flat_plane():
    # A barely-tilted plane: tiny slope, negligible relief -> flat_plain.
    return synthetic.plane(SHAPE, slope_x=0.001, slope_y=0.0005, dx=1.0, dy=1.0)


def _rough_field():
    # Gentle regional tilt plus large-amplitude white-noise roughness.
    base = synthetic.plane(SHAPE, slope_x=0.2, slope_y=0.1, dx=1.0, dy=1.0)
    return base + synthetic.rough_field(SHAPE, amplitude=5.0, seed=11)


def _smooth_hill():
    # A broad, smooth gaussian dome: real slope/relief but locally planar.
    return synthetic.gaussian_hill(SHAPE, amplitude=10.0, sigma=12.0, dx=1.0, dy=1.0)


def test_near_flat_plane_classifies_as_flat_plain():
    r = terrain_classify.classify(_near_flat_plane())
    assert r["type"] == "flat_plain", (r["type"], r["scores"])
    # Flat should dominate decisively over the runner-up.
    assert r["confidence"] > 0.2, r


def test_rough_field_classifies_as_rough_rugged():
    r = terrain_classify.classify(_rough_field())
    assert r["type"] == "rough_rugged", (r["type"], r["scores"])
    assert r["confidence"] > 0.2, r


def test_gaussian_hill_classifies_as_rolling_not_flat_not_rough():
    r = terrain_classify.classify(_smooth_hill())
    assert r["type"] == "rolling", (r["type"], r["scores"])
    assert r["type"] != "flat_plain"
    assert r["type"] != "rough_rugged"
    assert r["confidence"] > 0.2, r


def test_classify_returns_documented_keys_and_ranges():
    r = terrain_classify.classify(_smooth_hill())
    assert set(r) == RESULT_KEYS, set(r) ^ RESULT_KEYS
    assert r["type"] in terrain_classify.TYPES
    assert type(r["confidence"]) is float
    assert 0.0 <= r["confidence"] <= 1.0, r["confidence"]
    # evidence is a non-empty flat dict of the descriptor values the rules read
    assert isinstance(r["evidence"], dict) and r["evidence"]
    for k, v in r["evidence"].items():
        assert type(k) is str
        assert type(v) is float, (k, type(v))
    # scores: one float in [0, 1] per documented type
    assert isinstance(r["scores"], dict)
    assert set(r["scores"]) == set(terrain_classify.TYPES), set(r["scores"])
    for name, v in r["scores"].items():
        assert type(v) is float, (name, type(v))
        assert 0.0 <= v <= 1.0, (name, v)
    # the chosen type must be the argmax of the scores
    assert r["type"] == max(r["scores"], key=lambda n: r["scores"][n])


def test_classify_is_deterministic():
    z = _rough_field()
    assert terrain_classify.classify(z) == terrain_classify.classify(z)


def test_classify_bank_matches_classify_on_same_array():
    for z in (_near_flat_plane(), _rough_field(), _smooth_hill()):
        bank = descriptors.descriptor_bank(z)  # defaults dx=1.0, window=5
        from_bank = terrain_classify.classify_bank(bank)
        from_array = terrain_classify.classify(z)
        assert from_bank == from_array, (from_bank["type"], from_array["type"])
