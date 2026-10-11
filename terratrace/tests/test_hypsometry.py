"""Tests for the Strahler (1952) hypsometric (area-altitude) analysis module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_study.py / test_kh_roughness.py.
"""
import json

import numpy as np

from terratrace import hypsometry, synthetic


def test_linear_ramp_integral_half():
    # z[i, j] = i (a plane ramp): h' = i/(N-1) is symmetric about 0.5, so the
    # mean normalized height -- the hypsometric integral -- is exactly 0.5.
    z = synthetic.plane((64, 64), slope_y=1.0)          # z[i, j] = i
    hi = hypsometry.hypsometric_integral(z)
    assert abs(hi - 0.5) < 0.02, hi


def test_integral_equals_mean_normalized():
    # By definition HI == mean((z - min)/(max - min)) over finite cells.
    rng = np.random.default_rng(12345)
    z = rng.standard_normal((50, 60)) * 10.0 + 3.0
    expect = float(np.mean((z - z.min()) / (z.max() - z.min())))
    got = hypsometry.hypsometric_integral(z)
    assert abs(got - expect) < 1e-9, (got, expect)


def test_top_vs_bottom_heavy():
    # Nonlinear remaps of a uniform ramp: h'^0.3 pushes area to HIGH elevations
    # (top-heavy -> HI ~ 1/1.3 ~ 0.77); h'^3 pushes it LOW (bottom-heavy ->
    # HI ~ 1/4 ~ 0.25).
    base = np.linspace(0.0, 1.0, 120).reshape(120, 1) * np.ones((1, 120))
    top_heavy = base ** 0.3
    bottom_heavy = base ** 3.0
    hi_top = hypsometry.hypsometric_integral(top_heavy)
    hi_bot = hypsometry.hypsometric_integral(bottom_heavy)
    assert hi_top > 0.55, hi_top
    assert hi_bot < 0.45, hi_bot


def test_curve_monotone_bounds():
    z = synthetic.plane((128, 128), slope_y=1.0)        # ramp
    a, area = hypsometry.hypsometric_curve(z, nbins=100)
    assert a.ndim == 1 and area.ndim == 1
    assert a.shape == area.shape and a.shape[0] == 101   # both same length
    assert np.all(a >= 0.0) and np.all(a <= 1.0)
    assert np.all(area >= 0.0) and np.all(area <= 1.0)
    assert np.all(np.diff(a) > 0.0)                      # a ascending
    assert np.all(np.diff(area) <= 1e-12)                # non-increasing
    assert area[0] >= 0.999, area[0]                     # starts ~1.0 at a=0
    assert area[-1] <= 0.02, area[-1]                    # ends ~0.0 at a=1


def test_degenerate_constant():
    z = np.full((40, 40), 7.0)
    hi = hypsometry.hypsometric_integral(z)              # must not raise
    assert hi == 0.5, hi
    a, area = hypsometry.hypsometric_curve(z)
    assert a.shape == area.shape
    assert np.allclose(area, 0.5)
    sig = hypsometry.hypsometric_signature(z)
    assert sig["integral"] == 0.5
    assert sig["skew"] == 0.0 and sig["kurtosis"] == 0.0


def test_signature_contract_nan_safe():
    z = (synthetic.plane((40, 40), slope_x=0.1, slope_y=0.05)
         + synthetic.rough_field((40, 40), 1.0, seed=2))
    z[3, 4] = np.nan
    z[10, 20] = np.nan
    z[30, 30] = np.nan
    sig = hypsometry.hypsometric_signature(z)
    assert set(sig) == {"integral", "skew", "kurtosis", "curve"}, set(sig)
    assert type(sig["integral"]) is float
    assert type(sig["skew"]) is float
    assert type(sig["kurtosis"]) is float
    assert isinstance(sig["curve"], list) and len(sig["curve"]) == 11
    assert all(type(x) is float for x in sig["curve"])
    for key in ("integral", "skew", "kurtosis"):
        assert np.isfinite(sig[key]), (key, sig[key])
    assert all(np.isfinite(x) for x in sig["curve"]), sig["curve"]
    dumped = json.dumps(sig)                             # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert hypsometry.hypsometric_signature(z) == sig    # deterministic
