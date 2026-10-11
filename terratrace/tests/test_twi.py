"""Tests for the Beven & Kirkby (1979) Topographic Wetness Index module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_slope_area.py / test_drainage.py.

These exercise a purely GEOMETRIC area/slope composite (a steady-state
wetness-propensity index) of the sampled surface; nothing here is a claim of soil
moisture, water, hydrology, or erosion on any body.
"""
import json

import numpy as np

from terratrace import synthetic, twi

_SIG_KEYS = {"twi_mean", "twi_median", "twi_p10", "twi_p90", "twi_std"}


def test_gentler_plane_has_higher_twi():
    # Oracle 1 (the defining behaviour): at comparable contributing area, a
    # GENTLER slope has higher TWI than a STEEPER one. Both planes share the same
    # D8 flow geometry (steepest descent is due west regardless of magnitude), so
    # the contributing area `a` is identical cell-for-cell and TWI differs only
    # through tan(beta): gentle exceeds steep by exactly ln(0.20 / 0.02) = ln(10).
    g = synthetic.plane((80, 80), slope_x=0.02, dx=10.0)
    s = synthetic.plane((80, 80), slope_x=0.20, dx=10.0)
    assert twi.twi_signature(g)["twi_mean"] > twi.twi_signature(s)["twi_mean"]


def test_twi_monotone_decreasing_in_slope():
    # Oracle 2: across planes of increasing slope, twi_mean is STRICTLY
    # decreasing. `a` is identical across the four planes (same elevation order
    # => same depression-filled D8 routing), so twi_mean = C - ln(slope), which
    # falls monotonically as slope grows (all slopes are above the 1e-3 floor).
    slopes = [0.02, 0.05, 0.1, 0.2]
    means = [twi.twi_signature(synthetic.plane((80, 80), slope_x=sx, dx=10.0))["twi_mean"]
             for sx in slopes]
    for hi, lo in zip(means, means[1:]):
        assert hi > lo, means


def test_signature_contract():
    # Oracle 3: exact key set, float-typed values, JSON round-trip, and a second
    # call that serialises to byte-identical JSON tokens (determinism).
    z = (synthetic.plane((80, 80), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((80, 80), amplitude=2.0, seed=1))
    sig = twi.twi_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    for v in sig.values():
        assert type(v) is float, sig
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(twi.twi_signature(z, dx=10.0)) == dumped


def test_nan_safe():
    # Oracle 4: a few NaN cells raise nothing in either entry point; the field
    # keeps both NaN and finite cells and the signature stays finite/nan floats
    # that JSON round-trip.
    z = (synthetic.plane((80, 80), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((80, 80), amplitude=2.0, seed=1))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    field = twi.twi_field(z, dx=10.0)                          # must not raise
    assert field.shape == z.shape
    assert np.isnan(field).any()                               # NaNs propagate
    assert np.isfinite(field).any()                            # finite cells remain
    sig = twi.twi_signature(z, dx=10.0)                        # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    for v in sig.values():
        assert type(v) is float and (np.isfinite(v) or np.isnan(v)), sig
    assert json.loads(json.dumps(sig)) is not None
