"""Tests for the geomorphometric descriptor bank (dependency-free, assert-based).

Mirrors the plain ``def test_*()`` style of test_features.py: no pytest, no
network, small synthetic fixtures with known answers.
"""
import json

import numpy as np

from terratrace import descriptors, synthetic

MAP_KEYS = ("slope", "relief", "ruggedness", "profile_curvature",
            "plan_curvature", "mean_curvature", "vector_ruggedness")
SCALAR_KEYS = ("aspect_dispersion", "hypsometric_integral",
               "tpi_dispersion", "hurst_exponent")
SUMMARY_KEYS = {"mean", "std", "p10", "p50", "p90"}


def test_bank_on_plane_curvatures_zero_slope_positive():
    plane = synthetic.plane((40, 40), slope_x=0.3, slope_y=0.15, dx=1.0, dy=1.0)
    bank = descriptors.descriptor_bank(plane)
    for key in ("profile_curvature", "plan_curvature", "mean_curvature"):
        assert abs(bank[key]["mean"]) < 1e-6, (key, bank[key]["mean"])
    assert bank["vector_ruggedness"]["p50"] < 1e-6, bank["vector_ruggedness"]["p50"]
    slope = bank["slope"]
    assert all(np.isfinite(v) for v in slope.values()), slope
    for stat in ("mean", "p10", "p50", "p90"):
        assert slope[stat] > 0.0, (stat, slope[stat])


def test_bank_detects_roughness_vs_plane():
    plane = synthetic.plane((40, 40), slope_x=0.3, slope_y=0.1, dx=1.0, dy=1.0)
    rough = plane + synthetic.rough_field((40, 40), amplitude=1.0, seed=11)
    bp = descriptors.descriptor_bank(plane)
    br = descriptors.descriptor_bank(rough)
    assert br["vector_ruggedness"]["p50"] > bp["vector_ruggedness"]["p50"], (
        br["vector_ruggedness"]["p50"], bp["vector_ruggedness"]["p50"])
    assert br["ruggedness"]["mean"] > bp["ruggedness"]["mean"], (
        br["ruggedness"]["mean"], bp["ruggedness"]["mean"])


def test_bank_keys_types_and_json_serialisable():
    z = (synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((40, 40), amplitude=0.5, seed=1))
    bank = descriptors.descriptor_bank(z)
    expected = (set(MAP_KEYS) | set(SCALAR_KEYS) |
                {"structure_function", "surface_area_ratio",
                 "terrain_ruggedness_index", "landform_fraction"})
    assert set(bank) == expected, set(bank) ^ expected
    for key in MAP_KEYS:
        summ = bank[key]
        assert isinstance(summ, dict), key
        assert set(summ) == SUMMARY_KEYS, (key, set(summ))
        for v in summ.values():
            assert type(v) is float, (key, v, type(v))
    for key in SCALAR_KEYS:
        assert type(bank[key]) is float, (key, type(bank[key]))
    sf = bank["structure_function"]
    assert isinstance(sf, dict) and sf, "structure_function should be non-empty"
    for k, v in sf.items():
        assert type(k) is str, (k, type(k))
        assert type(v) is float, (k, v, type(v))
    dumped = json.dumps(bank)
    assert isinstance(dumped, str) and len(dumped) > 0
    assert json.loads(dumped)  # round-trips cleanly


def test_bank_is_deterministic():
    z = (synthetic.plane((40, 40), slope_x=0.25, slope_y=0.05)
         + synthetic.rough_field((40, 40), amplitude=0.7, seed=4))
    assert descriptors.descriptor_bank(z) == descriptors.descriptor_bank(z)


def test_summarize_map_all_nan_and_known_median():
    s = descriptors.summarize_map(np.full((5, 5), np.nan))
    assert set(s) == SUMMARY_KEYS
    assert all(np.isnan(v) for v in s.values()), s
    assert all(type(v) is float for v in s.values())

    k = descriptors.summarize_map(np.array([10.0, 20.0, 30.0]))
    assert abs(k["p50"] - 20.0) < 1e-12, k["p50"]
    assert abs(k["mean"] - 20.0) < 1e-12, k["mean"]

    # nan-aware: only finite values contribute to the median.
    km = descriptors.summarize_map(np.array([10.0, 20.0, 30.0, np.nan]))
    assert abs(km["p50"] - 20.0) < 1e-12, km["p50"]
    assert np.isfinite(km["mean"])


def test_bank_vector_matches_bank_headline_scalars():
    z = (synthetic.plane((40, 40), slope_x=0.3, slope_y=0.1)
         + synthetic.rough_field((40, 40), amplitude=0.8, seed=2))
    bank = descriptors.descriptor_bank(z)
    vec = descriptors.bank_vector(z)
    assert len(vec) == len(descriptors.BANK_VECTOR_FIELDS) == 7, len(vec)
    assert all(type(x) is float for x in vec)
    expected = (
        bank["slope"]["p50"],
        bank["ruggedness"]["p50"],
        bank["mean_curvature"]["std"],
        bank["vector_ruggedness"]["p50"],
        bank["aspect_dispersion"],
        bank["hypsometric_integral"],
        bank["hurst_exponent"],
    )
    assert vec == expected, (vec, expected)


# --- added analysis-layer descriptors wired into the bank --------------------

def test_bank_has_added_descriptors_rough_gt_plane_sar_and_serialises():
    plane = synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1, dx=1.0, dy=1.0)
    rough = plane + synthetic.rough_field((40, 40), amplitude=1.0, seed=13)
    bp = descriptors.descriptor_bank(plane)
    br = descriptors.descriptor_bank(rough)

    for key in ("surface_area_ratio", "terrain_ruggedness_index", "landform_fraction"):
        assert key in bp, key
    # the two added map summaries are {mean,std,p10,p50,p90} dicts of plain floats
    for key in ("surface_area_ratio", "terrain_ruggedness_index"):
        assert set(bp[key]) == SUMMARY_KEYS, (key, set(bp[key]))
        assert all(type(v) is float for v in bp[key].values()), key
    # landform_fraction is a dict of plain floats summing to ~1 (or degenerate 0)
    lf = bp["landform_fraction"]
    assert set(lf) == {"ridge", "valley", "flat"}, set(lf)
    assert all(type(v) is float for v in lf.values()), lf

    # a rough field exposes more 3-D surface area per unit plan area than a plane
    assert br["surface_area_ratio"]["mean"] > bp["surface_area_ratio"]["mean"], (
        br["surface_area_ratio"]["mean"], bp["surface_area_ratio"]["mean"])
    assert br["terrain_ruggedness_index"]["mean"] > bp["terrain_ruggedness_index"]["mean"]

    # the whole extended bank still json.dumps and round-trips
    dumped = json.dumps(br)
    assert isinstance(dumped, str) and json.loads(dumped)
