"""Tests for the openness-difference slope-position module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_openness.py / test_slope_area.py. The repo's runner discovers and calls
every top-level ``test_*`` function in this module.

These exercise a purely GEOMETRIC slope-position measure derived from
line-of-sight openness (Yokoyama 2002); nothing here is a geological,
surface-process, or mission claim on any body.
"""
import json

import numpy as np

from terratrace import openness, openness_difference as od, synthetic

_SIG_KEYS = {"slopepos_mean", "slopepos_std", "slopepos_p10", "slopepos_p90",
             "ridge_fraction", "valley_fraction", "midslope_fraction"}


def _radial(n=81, sign=-1.0):
    """Radial cone / bowl ``z = sign * hypot(i - c, j - c)``, centre ``c=n//2``.

    ``sign = -1`` -> a cone with its PEAK at the centre (surface slopes away
    downhill); ``sign = +1`` -> a bowl with its PIT at the centre. Returns
    ``(z, c)`` where ``c`` is the centre row/col index.
    """
    c = n // 2
    ii, jj = np.indices((n, n))
    r = np.hypot(ii - c, jj - c).astype(float)
    return sign * r, c


def test_cone_peak_is_ridge_positive():
    # Oracle 1: a cone peaking at the centre is convex -> ridge-positive.
    z, c = _radial(81, sign=-1.0)
    d = od.openness_difference_field(z)
    assert d.shape == z.shape, d.shape
    assert d[c, c] > 0.0, d[c, c]
    sig = od.openness_difference_signature(z)
    assert sig["slopepos_mean"] > 0.0, sig
    assert sig["ridge_fraction"] > sig["valley_fraction"], sig


def test_bowl_pit_is_valley_negative():
    # Oracle 2: a bowl with its pit at the centre is concave -> valley-negative.
    z, c = _radial(81, sign=+1.0)
    d = od.openness_difference_field(z)
    assert d[c, c] < 0.0, d[c, c]
    sig = od.openness_difference_signature(z)
    assert sig["slopepos_mean"] < 0.0, sig
    assert sig["valley_fraction"] > sig["ridge_fraction"], sig


def test_plane_is_midslope():
    # Oracle 3: a uniform planar tilt has Phi ~ Psi -> D ~ 0 everywhere, so the
    # mean slope position is near zero and midslope dominates both tails.
    z = synthetic.plane((80, 80), slope_x=0.03, dx=10.0)
    sig = od.openness_difference_signature(z, dx=10.0)
    assert abs(sig["slopepos_mean"]) < 1.0, sig
    assert sig["midslope_fraction"] > sig["ridge_fraction"], sig
    assert sig["midslope_fraction"] > sig["valley_fraction"], sig


def test_flat_surface_difference_is_zero():
    # A flat surface has Phi = Psi = 90 exactly -> D is identically zero.
    z = np.zeros((30, 30))
    d = od.openness_difference_field(z, radius=5)
    assert np.max(np.abs(d)) < 1e-6, np.max(np.abs(d))
    sig = od.openness_difference_signature(z, radius=5)
    assert abs(sig["slopepos_mean"]) < 1e-6, sig
    assert sig["midslope_fraction"] == 1.0, sig


def test_field_is_positive_minus_negative():
    # The field is exactly the reused openness fields differenced.
    rng = np.random.default_rng(11)
    z = 3.0 * rng.standard_normal((40, 40))
    fields = openness.openness(z)
    d = od.openness_difference_field(z)
    assert np.allclose(d, fields["positive"] - fields["negative"],
                       atol=1e-9, rtol=0.0)


def test_signature_contract():
    # Oracle 4: keys / types, fractions in [0, 1] that partition to 1,
    # JSON-serialisable, deterministic.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = od.openness_difference_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig) ^ _SIG_KEYS
    for key, value in sig.items():
        assert type(value) is float, (key, type(value))
    assert sig["slopepos_p90"] >= sig["slopepos_p10"], sig
    for frac in ("ridge_fraction", "valley_fraction", "midslope_fraction"):
        assert 0.0 <= sig[frac] <= 1.0, (frac, sig[frac])
    total = sig["ridge_fraction"] + sig["valley_fraction"] + sig["midslope_fraction"]
    assert abs(total - 1.0) < 1e-9, total
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(od.openness_difference_signature(z, dx=10.0)) == dumped


def test_nan_safe():
    # Oracle 5: a few NaN cells raise nothing in either entry point and the
    # 90-degree fallback keeps the differenced field finite.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    d = od.openness_difference_field(z)                        # must not raise
    assert d.shape == z.shape
    assert np.all(np.isfinite(d)), "the 90-degree fallback keeps D finite"
    sig = od.openness_difference_signature(z)                  # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    assert json.loads(json.dumps(sig)) is not None
