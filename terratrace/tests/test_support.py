"""Common-support aggregation fixtures."""
import numpy as np
from terratrace import support


def test_constant_aggregates_to_constant():
    z = np.full((8, 8), 7.0)
    agg, rec = support.block_aggregate(z, factor=2, native_posting_m=25.0)
    assert agg.shape == (4, 4)
    assert np.allclose(agg, 7.0)
    assert rec.factor == 2
    assert rec.target_support_m == 50.0
    assert rec.valid_fraction == 1.0


def test_known_block_mean():
    z = np.array([[0.0, 2.0], [4.0, 6.0]])
    agg, _ = support.block_aggregate(z, factor=2, native_posting_m=10.0)
    assert agg.shape == (1, 1)
    assert abs(agg[0, 0] - 3.0) < 1e-12


def test_nodata_block_becomes_nan_and_tracks_fraction():
    z = np.array([
        [np.nan, np.nan, 1.0, 1.0],
        [np.nan, np.nan, 1.0, 1.0],
        [2.0, 2.0, 3.0, 3.0],
        [2.0, 2.0, 3.0, 3.0],
    ])
    agg, rec = support.block_aggregate(z, factor=2, native_posting_m=30.0, min_valid=0.5)
    assert np.isnan(agg[0, 0])          # fully-nodata block
    assert abs(agg[0, 1] - 1.0) < 1e-12
    assert abs(rec.valid_fraction - 0.75) < 1e-12


def test_common_factor():
    assert support.common_factor(25.0, 25.0, 100.0) == (4, 4)
    assert support.common_factor(10.0, 30.0, 90.0) == (9, 3)
