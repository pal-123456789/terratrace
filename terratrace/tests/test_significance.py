"""Resampling-significance fixtures (dependency-free, assert-based)."""
import numpy as np
from terratrace import significance


def test_a_from_ref_distribution_is_significantly_closer():
    rng = np.random.default_rng(42)
    ref = rng.normal(0.0, 1.0, 800)
    a = rng.normal(0.0, 1.0, 800)       # same law as ref
    b = rng.normal(3.0, 1.0, 800)       # clearly shifted
    res = significance.permutation_closer_test(ref, a, b, n_perm=600, seed=0)
    assert res["a_closer"] is True, res
    assert res["significant"] is True, res
    assert res["p_value_one_sided"] < 0.05, res
    assert significance.effect_size(ref, a, b) > 0.0


def test_same_distribution_is_not_significant():
    rng = np.random.default_rng(7)
    ref = rng.normal(0.0, 1.0, 800)
    a = rng.normal(0.0, 1.0, 800)
    b = rng.normal(0.0, 1.0, 800)
    res = significance.permutation_closer_test(ref, a, b, n_perm=600, seed=0)
    assert res["significant"] is False, res
    assert res["p_value_one_sided"] > 0.1, res


def test_bootstrap_ci_ordering_and_finite():
    rng = np.random.default_rng(1)
    ref = rng.normal(0.0, 1.0, 500)
    x = rng.normal(0.5, 1.0, 500)
    res = significance.bootstrap_distance_ci(ref, x, n_boot=500, seed=0)
    assert np.isfinite(res["lo"])
    assert np.isfinite(res["median"])
    assert np.isfinite(res["hi"])
    assert res["lo"] <= res["median"] <= res["hi"], res


def test_bootstrap_ci_identical_sample_is_near_zero():
    rng = np.random.default_rng(2)
    ref = rng.normal(0.0, 1.0, 1000)
    res = significance.bootstrap_distance_ci(ref, ref, n_boot=500, seed=0)
    assert res["median"] < 0.25, res


def test_determinism_same_seed_identical():
    rng = np.random.default_rng(3)
    ref = rng.normal(0.0, 1.0, 400)
    a = rng.normal(0.0, 1.0, 400)
    b = rng.normal(1.5, 1.0, 400)
    r1 = significance.permutation_closer_test(ref, a, b, n_perm=400, seed=11)
    r2 = significance.permutation_closer_test(ref, a, b, n_perm=400, seed=11)
    assert r1 == r2, (r1, r2)
    c1 = significance.bootstrap_distance_ci(ref, a, n_boot=400, seed=11)
    c2 = significance.bootstrap_distance_ci(ref, a, n_boot=400, seed=11)
    assert c1 == c2, (c1, c2)


def test_empty_sample_guard_does_not_raise():
    rng = np.random.default_rng(4)
    ref = rng.normal(0.0, 1.0, 100)
    b = rng.normal(0.0, 1.0, 100)
    res = significance.permutation_closer_test(ref, [], b, n_perm=200, seed=0)
    assert np.isnan(res["a_distance"]), res
    assert np.isnan(res["b_distance"]), res
    assert res["p_value_one_sided"] == 1.0, res
    assert res["significant"] is False, res
