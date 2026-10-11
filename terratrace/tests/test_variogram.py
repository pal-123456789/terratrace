"""Tests for the Matheron (1963) empirical-semivariogram signature module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring test_slope_area.py.

These summarise the geostatistical second-order structure (semivariance) of the
sampled height field; nothing here is a process, traversability or mission claim
on any body.
"""
import json

import numpy as np

from terratrace import variogram, synthetic

_SIG_KEYS = {"sill", "nugget", "range_m", "vario_loglog_slope", "aniso_ratio"}


def test_white_noise_nugget_dominated():
    # Oracle 1: an uncorrelated (white-noise) field has a FLAT semivariogram
    # pinned at the sill from the first lag -- nearly all variance is nugget and
    # the range collapses to the shortest lag. (rough_field with amplitude 1 and
    # seed 0 is exactly default_rng(0).standard_normal, i.e. white noise.)
    z = np.random.default_rng(0).standard_normal((80, 80))
    sig = variogram.variogram_signature(z)                 # dx defaults to 1.0
    assert np.isfinite(sig["sill"]) and sig["sill"] > 0.0, sig
    assert np.isfinite(sig["nugget"]), sig
    assert sig["nugget"] > 0.5 * sig["sill"], sig
    assert sig["range_m"] <= 2.0, sig                      # <= 2*dx with dx == 1


def test_smooth_plane_rising_tiny_nugget():
    # Oracle 2: a smooth planar ramp has a semivariogram that RISES with lag
    # (gamma ~ h^2 along the gradient) with effectively zero nugget.
    z = synthetic.plane((80, 80), slope_x=0.05, dx=10.0)
    sig = variogram.variogram_signature(z, dx=10.0)
    assert np.isfinite(sig["sill"]) and sig["sill"] > 0.0, sig
    assert sig["nugget"] < 0.05 * sig["sill"], sig          # nugget ~ 0 vs sill
    assert np.isfinite(sig["vario_loglog_slope"]), sig
    assert sig["vario_loglog_slope"] > 0.5, sig             # gamma grows w/ lag


def test_sill_equals_variance():
    # Oracle 3: for a stationary field the sill is the field variance.
    z = synthetic.rough_field((64, 64), amplitude=2.0, seed=3)
    sig = variogram.variogram_signature(z, dx=5.0)
    assert abs(sig["sill"] - float(np.nanvar(z))) < 1e-6, sig


def test_signature_contract():
    # Oracle 4a: exact keys, float types, JSON round-trip, deterministic recall.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=4))
    sig = variogram.variogram_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    for key in _SIG_KEYS:
        assert type(sig[key]) is float, (key, type(sig[key]))
    dumped = json.dumps(sig)                                # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(variogram.variogram_signature(z, dx=10.0)) == dumped


def test_semivariogram_arrays():
    # Oracle 4b: the raw curve is two equal-length 1-D float arrays, lag = k*dx,
    # gamma non-negative where finite.
    z = synthetic.plane((50, 50), slope_x=0.04, dx=8.0)
    lags, gamma = variogram.semivariogram(z, dx=8.0, n_lags=10)
    assert lags.shape == gamma.shape == (10,)
    assert lags.ndim == 1 and gamma.ndim == 1
    assert np.allclose(lags, np.arange(1, 11) * 8.0)
    fin = np.isfinite(gamma)
    assert np.any(fin)
    assert np.all(gamma[fin] >= 0.0)


def test_nan_safe():
    # Oracle 4c: a few NaN cells raise nothing and the contract still holds.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    lags, gamma = variogram.semivariogram(z, dx=10.0)       # must not raise
    assert lags.shape == gamma.shape
    sig = variogram.variogram_signature(z, dx=10.0)          # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    assert np.isfinite(sig["sill"]), sig
    assert json.loads(json.dumps(sig)) is not None
