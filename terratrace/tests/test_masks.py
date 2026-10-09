"""Mask fixtures."""
import numpy as np
from terratrace import masks


def test_mask_values_drops_zeros():
    z = np.array([[0.0, 1.0], [2.0, 0.0]])
    out = masks.apply_masks(z, mask_values=[0.0])
    assert np.isnan(out[0, 0]) and np.isnan(out[1, 1])
    assert out[0, 1] == 1.0 and out[1, 0] == 2.0


def test_mask_below_and_above():
    z = np.array([-5.0, 0.0, 10.0, 100.0])
    out = masks.apply_masks(z, mask_below=0.5, mask_above=50.0)
    assert np.isnan(out[0]) and np.isnan(out[1])   # below 0.5
    assert out[2] == 10.0
    assert np.isnan(out[3])                          # above 50


def test_zero_fraction():
    z = np.array([0.0, 0.0, 0.0, 1.0])             # 75% zeros
    assert abs(masks.zero_fraction(z) - 0.75) < 1e-12
    z2 = np.array([np.nan, 0.0, 2.0])              # finite: {0,2} -> 50%
    assert abs(masks.zero_fraction(z2) - 0.5) < 1e-12


def test_apply_masks_does_not_mutate_input():
    z = np.array([0.0, 1.0])
    _ = masks.apply_masks(z, mask_values=[0.0])
    assert z[0] == 0.0   # original untouched
