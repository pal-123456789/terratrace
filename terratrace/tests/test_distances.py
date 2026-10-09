"""Distribution-distance fixtures."""
import numpy as np
from terratrace import distances


def test_wasserstein_identical_is_zero():
    x = np.arange(1000, dtype=float)
    assert abs(distances.wasserstein1(x, x)) < 1e-9


def test_wasserstein_shift_equals_offset():
    x = np.arange(1000, dtype=float)
    y = x + 5.0
    assert abs(distances.wasserstein1(x, y) - 5.0) < 1e-6


def test_ks_identical_zero_and_disjoint_one():
    x = np.arange(100, dtype=float)
    assert abs(distances.ks_distance(x, x)) < 1e-12
    y = x + 1000.0
    assert abs(distances.ks_distance(x, y) - 1.0) < 1e-12


def test_quantile_fingerprint_keys():
    fp = distances.quantile_fingerprint(np.arange(100, dtype=float))
    assert set(fp) == {"0.05", "0.25", "0.5", "0.75", "0.95"}


def test_nan_is_ignored():
    x = np.array([1.0, 2.0, np.nan, 3.0])
    y = np.array([1.0, 2.0, 3.0])
    assert abs(distances.wasserstein1(x, y)) < 1e-9


def test_normalized_distance_degenerate_scale_is_finite():
    x = np.zeros(5)
    y = np.concatenate([np.zeros(4), [100.0]])   # zero IQR but real spread
    d = distances.normalized_distance(x, y)
    assert np.isfinite(d) and d < 1e3, d


def test_normalized_distance_all_constant_is_zero():
    x = np.full(10, 5.0)
    y = np.full(10, 5.0)
    assert distances.normalized_distance(x, y) == 0.0
