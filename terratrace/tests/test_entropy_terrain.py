"""Tests for the Shannon (1948) terrain-entropy descriptor
(``terratrace.entropy_terrain``). Dependency-free: plain ``def test_*()``,
assert-based, no pytest, no network -- small synthetic surfaces with known
analytic answers, mirroring the style of test_study.py / test_hypsometry.py.
"""
import json

import numpy as np

from terratrace import entropy_terrain, synthetic


def test_constant_zero_slope_entropy():
    # A relief-free field has zero slope everywhere -> all slope mass in one bin
    # -> slope entropy (and its normalized form) are exactly zero.
    z = synthetic.constant((64, 64), 5.0)
    sig = entropy_terrain.entropy_signature(z)
    assert sig["slope_entropy"] == 0.0, sig["slope_entropy"]
    assert sig["slope_entropy_norm"] == 0.0, sig["slope_entropy_norm"]


def test_uniform_high_entropy():
    # A seeded random field has slope magnitudes spread broadly across the range,
    # so its normalized slope entropy is high (well above the 0.5 midpoint).
    z = synthetic.rough_field((64, 64), amplitude=1.0, seed=0)
    sig = entropy_terrain.entropy_signature(z)
    assert sig["slope_entropy_norm"] > 0.5, sig["slope_entropy_norm"]


def test_diverse_greater_than_simple():
    # A single planar ramp is one constant slope -> zero slope entropy; a complex
    # multi-scale surface spreads slope mass across many bins -> strictly greater.
    simple = synthetic.plane((96, 96), slope_x=0.1, slope_y=0.05)
    complex_ = synthetic.plane((96, 96), slope_x=0.02, slope_y=0.01)
    for amp, seed in [(6.0, 1), (3.0, 2), (1.5, 3), (0.7, 4)]:
        complex_ = complex_ + synthetic.rough_field((96, 96), amp, seed)
    h_simple = entropy_terrain.entropy_signature(simple)["slope_entropy"]
    h_complex = entropy_terrain.entropy_signature(complex_)["slope_entropy"]
    assert h_simple == 0.0, h_simple
    assert h_complex > h_simple, (h_complex, h_simple)


def test_bounds():
    # Signature contract: four plain-float keys, raw entropies >= 0, normalized
    # entropies in [0, 1], finite, JSON-serialisable and deterministic.
    z = (synthetic.plane((80, 80), slope_x=0.05, slope_y=0.02)
         + synthetic.rough_field((80, 80), 1.5, seed=11))
    sig = entropy_terrain.entropy_signature(z)
    assert set(sig) == {"slope_entropy", "elevation_entropy",
                        "slope_entropy_norm", "elevation_entropy_norm"}, set(sig)
    assert all(type(v) is float for v in sig.values()), sig
    assert sig["slope_entropy"] >= 0.0 and sig["elevation_entropy"] >= 0.0, sig
    for key in ("slope_entropy_norm", "elevation_entropy_norm"):
        assert 0.0 <= sig[key] <= 1.0, (key, sig[key])
    assert all(np.isfinite(v) for v in sig.values()), sig
    dumped = json.dumps(sig)                                 # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) == sig
    assert entropy_terrain.entropy_signature(z) == sig       # deterministic


def test_shannon_known():
    # Two equally-populated bins -> maximal 1-bit entropy. With nbins=2 over the
    # auto range [0, 1], half the mass at 0 and half at 1 give p = [0.5, 0.5] and
    # H = -(0.5*log2 0.5 + 0.5*log2 0.5) = 1.0 bit exactly.
    values = np.array([0.0] * 500 + [1.0] * 500)
    h = entropy_terrain.shannon_entropy(values, nbins=2)
    assert abs(h - 1.0) < 1e-9, h


def test_nan_safe():
    # A few NaN cells must not raise and must leave every output finite, both for
    # the full signature and for the scalar helper on a NaN-bearing grid.
    z = (synthetic.plane((48, 48), slope_x=0.08, slope_y=0.03)
         + synthetic.rough_field((48, 48), 1.0, seed=5))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 2] = np.nan
    sig = entropy_terrain.entropy_signature(z)               # must not raise
    assert all(np.isfinite(v) for v in sig.values()), sig
    h = entropy_terrain.shannon_entropy(z, nbins=64)
    assert np.isfinite(h) and h >= 0.0, h
