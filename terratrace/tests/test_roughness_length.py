"""Tests for the Shepard et al. (2001) RMS-deviation roughness-length module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_slope_area.py / test_drainage.py.

These summarise a purely GEOMETRIC RMS-deviation (Allan-deviation) roughness of
the sampled height field; nothing here is a radar-backscatter, trafficability,
or mission claim.
"""
import json

import numpy as np

from terratrace import roughness_length as rl, synthetic

_SIG_KEYS = {"rms_height", "rms_slope", "hurst_deviogram", "roughness_length_m"}


def test_smooth_ramp_hurst_one_and_constant_slope():
    # Oracle 1: a planar ramp has nu(Dx) proportional to Dx, so the deviogram
    # Hurst is ~1, and the gradient magnitude equals the ramp slope (0.1).
    z = synthetic.plane((80, 80), slope_x=0.1, dx=10.0)
    sig = rl.roughness_length_signature(z, dx=10.0)
    assert np.isfinite(sig["hurst_deviogram"]), sig
    assert 0.8 <= sig["hurst_deviogram"] <= 1.2, sig["hurst_deviogram"]
    assert abs(sig["rms_slope"] - 0.1) < 0.005, sig["rms_slope"]


def test_white_noise_hurst_near_zero():
    # Oracle 2: white noise decorrelates within one pixel, so nu(Dx) is flat and
    # the deviogram Hurst is ~0.
    z = np.random.default_rng(1).standard_normal((80, 80))
    sig = rl.roughness_length_signature(z)
    assert np.isfinite(sig["hurst_deviogram"]), sig
    assert sig["hurst_deviogram"] < 0.3, sig["hurst_deviogram"]


def test_rms_height_monotone_in_amplitude():
    # Oracle 3: scaling the same (seeded) rough field by a larger amplitude
    # raises the detrended RMS height strictly.
    heights = [
        rl.roughness_length_signature(
            synthetic.rough_field((80, 80), amplitude=a, seed=11))["rms_height"]
        for a in (0.5, 1.0, 2.0, 4.0)
    ]
    assert all(np.isfinite(h) for h in heights), heights
    assert all(b > a for a, b in zip(heights, heights[1:])), heights


def test_signature_contract():
    # Oracle 4a: keys/types, JSON-serialisable, deterministic.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = rl.roughness_length_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    for key in _SIG_KEYS:
        assert type(sig[key]) is float, (key, type(sig[key]))
    dumped = json.dumps(sig)
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert json.dumps(rl.roughness_length_signature(z, dx=10.0)) == dumped


def test_profile_shapes_and_lags():
    # Oracle 4b: the deviation profile returns equal-length 1-D arrays with
    # finite, strictly increasing lags in metres (k*dx) and finite nu.
    z = (synthetic.plane((50, 50), slope_x=0.04, dx=8.0)
         + synthetic.rough_field((50, 50), amplitude=1.0, seed=5))
    lags_m, nu = rl.rms_deviation_profile(z, dx=8.0, n_lags=12)
    assert lags_m.shape == nu.shape and lags_m.ndim == 1
    assert lags_m.size == 12
    assert np.all(np.isfinite(lags_m)) and np.all(np.isfinite(nu))
    assert np.all(lags_m > 0.0) and np.all(np.diff(lags_m) > 0.0)
    assert np.allclose(lags_m, np.arange(1, 13) * 8.0)


def test_nan_safe():
    # Oracle 4c: a few NaN cells raise nothing in either entry point.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    lags_m, nu = rl.rms_deviation_profile(z, dx=10.0)
    assert np.all(np.isfinite(lags_m)) and np.all(np.isfinite(nu))
    sig = rl.roughness_length_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    assert json.loads(json.dumps(sig)) is not None
