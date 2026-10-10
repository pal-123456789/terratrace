"""Spatial-autocorrelation fixtures with known qualitative answers.

White noise decorrelates immediately; a broad smooth hill stays correlated over
many lags. These checks pin that contrast and the data-driven block size, with
no network or challenge data.
"""
import numpy as np
from terratrace import autocorr, synthetic


def test_white_noise_decorrelates_immediately():
    noise = synthetic.rough_field((48, 48), amplitude=1.0, seed=1)
    cl = autocorr.correlation_length(noise, max_lag=20, dx=1.0)
    assert cl["length_px"] <= 2, cl["length_px"]
    assert autocorr.suggest_block_size(noise, min_block=2, max_block=16) == 2


def test_smooth_hill_stays_correlated_longer_than_noise():
    noise = synthetic.rough_field((48, 48), amplitude=1.0, seed=2)
    hill = synthetic.gaussian_hill((48, 48), amplitude=40.0, sigma=10.0)
    noise_len = autocorr.correlation_length(noise, max_lag=20)["length_px"]
    hill_len = autocorr.correlation_length(hill, max_lag=20)["length_px"]
    assert hill_len > noise_len, (hill_len, noise_len)
    assert autocorr.suggest_block_size(hill, min_block=2, max_block=16) > 2


def test_curve_lag0_is_one_and_bounded_and_ordered():
    noise = synthetic.rough_field((48, 48), amplitude=1.0, seed=3)
    hill = synthetic.gaussian_hill((48, 48), amplitude=40.0, sigma=10.0)
    cn = autocorr.autocorrelation_curve(noise, max_lag=20, dx=1.0)
    ch = autocorr.autocorrelation_curve(hill, max_lag=20, dx=1.0)
    assert cn[0.0] == 1.0
    assert ch[0.0] == 1.0
    for curve in (cn, ch):
        for v in curve.values():
            assert v <= 1.0 + 1e-9, v
    # a smoother field is more correlated at the first lag than white noise
    assert ch[1.0] > cn[1.0], (ch[1.0], cn[1.0])


def test_suggest_block_size_is_int_in_range():
    hill = synthetic.gaussian_hill((48, 48), amplitude=40.0, sigma=10.0)
    blk = autocorr.suggest_block_size(hill, min_block=2, max_block=16)
    assert isinstance(blk, int), type(blk)
    assert 2 <= blk <= 16, blk


def test_curve_is_deterministic():
    hill = synthetic.gaussian_hill((48, 48), amplitude=40.0, sigma=10.0)
    c1 = autocorr.autocorrelation_curve(hill, max_lag=20, dx=1.0)
    c2 = autocorr.autocorrelation_curve(hill, max_lag=20, dx=1.0)
    assert c1 == c2
