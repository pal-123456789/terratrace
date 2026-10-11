"""Tests for the Flint (1974) slope-area concavity-signature module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_drainage.py / test_hypsometry.py.

These exercise a purely GEOMETRIC slope-versus-contributing-area scaling of the
sampled surface; nothing here is a claim of fluvial, water, or erosion processes
on any body.
"""
import json

import numpy as np

from terratrace import slope_area, synthetic

_SIG_KEYS = {"flint_theta", "r2", "log_ks", "n_bins_used"}


def _concave_down_area(shape, dx=10.0, p=2.0, c=1.0e-3):
    """A concave profile whose slope FLATTENS as contributing area grows.

    ``z(i, j) = c * (D - x_j)^p`` with ``x_j = j*dx`` and ``D = cols*dx``,
    constant along rows. Elevation is highest at column 0 and falls monotonically
    with the column index, so the depression-filled D8 flow runs toward higher
    columns and the contributing area grows downstream, while the local slope
    ``|dz/dx| = c*p*(D - x)^(p-1)`` DECREASES downstream (``p > 1``). Slope thus
    falls as area grows -- a concave slope-area relation with ``theta > 0``.
    """
    rows, cols = shape
    x = np.arange(cols) * float(dx)
    d_cap = cols * float(dx)
    profile = c * (d_cap - x) ** p
    return np.repeat(profile[None, :], rows, axis=0)


def test_concave_profile_positive_theta():
    # Oracle 1: slope flattens downstream as area grows -> positive concavity.
    z = _concave_down_area((100, 100), dx=10.0, p=2.0)
    sig = slope_area.slope_area_signature(z, dx=10.0)
    assert sig["n_bins_used"] >= 2, sig
    assert np.isfinite(sig["flint_theta"]), sig
    assert sig["flint_theta"] > 0.0, sig["flint_theta"]
    assert sig["r2"] > 0.3, sig["r2"]


def test_uniform_slope_theta_near_zero():
    # Oracle 2: a constant-gradient planar ramp has identical slope everywhere,
    # so slope does NOT vary with contributing area. Documented behaviour ->
    # flint_theta is NaN (zero slope variance => the Flint relation is
    # undefined); a near-zero theta would be equally acceptable.
    z = synthetic.plane((80, 80), slope_x=0.05, dx=10.0)
    sig = slope_area.slope_area_signature(z, dx=10.0)
    theta = sig["flint_theta"]
    assert np.isnan(theta) or abs(theta) < 0.2, sig


def test_signature_contract():
    # Oracle 3: keys/types, JSON-serialisable, deterministic, >= 2 bins used.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = slope_area.slope_area_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    assert type(sig["flint_theta"]) is float
    assert type(sig["r2"]) is float
    assert type(sig["log_ks"]) is float
    assert type(sig["n_bins_used"]) is int
    assert sig["n_bins_used"] >= 2, sig
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(slope_area.slope_area_signature(z, dx=10.0)) == dumped


def test_arrays_finite():
    # Oracle 4: equal-length finite arrays with A > 0 and S >= 0.
    z = (synthetic.plane((50, 50), slope_x=0.04, dx=8.0)
         + synthetic.rough_field((50, 50), amplitude=1.0, seed=5))
    area, slope = slope_area.slope_area_arrays(z, dx=8.0)
    assert area.shape == slope.shape                           # equal length
    assert area.ndim == 1 and area.size > 0
    assert np.all(np.isfinite(area)) and np.all(np.isfinite(slope))
    assert np.all(area > 0.0)
    assert np.all(slope >= 0.0)


def test_nan_safe():
    # Oracle 5: a few NaN cells raise nothing in either entry point.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    area, slope = slope_area.slope_area_arrays(z, dx=10.0)      # must not raise
    assert np.all(np.isfinite(area)) and np.all(np.isfinite(slope))
    sig = slope_area.slope_area_signature(z, dx=10.0)           # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    assert json.loads(json.dumps(sig)) is not None
