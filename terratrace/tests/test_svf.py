"""Tests for the Sky-View Factor (Zakšek, Oštir & Kokalj 2011) module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_openness.py / test_slope_area.py. The repo's runner discovers and calls
every top-level ``test_*`` function in this module.

These exercise a purely GEOMETRIC visible-sky fraction derived from horizon
elevation angles; nothing here is an insolation, thermal, illumination, or
mission claim on any body.
"""
import json

import numpy as np

from terratrace import svf, synthetic

_SIG_KEYS = {"svf_mean", "svf_median", "svf_p10", "svf_p90", "svf_min"}


def _radial(shape):
    """Radial distance (in cells) from the grid centre, plus the centre index."""
    rows, cols = shape
    centre = (rows // 2, cols // 2)
    ii, jj = np.indices(shape)
    return np.hypot(ii - centre[0], jj - centre[1]), centre


def _bowl(shape=(61, 61), depth=10.0):
    """Radial bowl: rim high, centre low (``z = depth * r / r.max()``)."""
    r, centre = _radial(shape)
    return depth * r / r.max(), centre


def _cone(shape=(41, 41)):
    """Isolated peak at the centre (``z = -r``), descending outward."""
    r, centre = _radial(shape)
    return -r, centre


def test_flat_plane_is_one():
    # Oracle 1: a perfectly flat surface has every horizon angle 0, so the
    # sky-view factor is exactly 1.0 at every cell (and the mean is 1.0).
    z = np.zeros((60, 60))
    field = svf.svf_field(z)
    assert field.shape == z.shape
    assert np.all(np.isfinite(field)), "flat surface has no NaN output"
    assert np.max(np.abs(field - 1.0)) < 1e-9, np.max(np.abs(field - 1.0))
    sig = svf.svf_signature(z)
    assert abs(sig["svf_mean"] - 1.0) < 1e-9, sig["svf_mean"]


def test_bowl_below_one_and_monotone_with_depth():
    # Oracle 2: inside a pit terrain rises above the horizontal in every
    # direction, so the centre SVF is < 1; a deeper (steeper) bowl blocks more
    # sky everywhere, so its mean SVF is strictly lower than a shallow one's.
    shallow, centre = _bowl(depth=5.0)
    deep, _ = _bowl(depth=40.0)
    fs = svf.svf_field(shallow)
    fd = svf.svf_field(deep)
    assert fs[centre] < 1.0, fs[centre]
    assert fd[centre] < 1.0, fd[centre]
    mean_shallow = svf.svf_signature(shallow)["svf_mean"]
    mean_deep = svf.svf_signature(deep)["svf_mean"]
    assert mean_deep < mean_shallow, (mean_deep, mean_shallow)


def test_isolated_peak_is_open():
    # Oracle 3: nothing rises above an isolated apex, so its horizon is entirely
    # open and the apex SVF is ~1 (exactly 1.0 here).
    z, centre = _cone()
    field = svf.svf_field(z)
    assert field[centre] > 0.9, field[centre]


def test_range_and_signature_contract():
    # Oracle 4: finite values in [0, 1]; exact keys/types; JSON round-trip;
    # deterministic second call.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01)
         + synthetic.rough_field((64, 64), amplitude=1.5, seed=11))
    field = svf.svf_field(z)
    finite = field[np.isfinite(field)]
    assert finite.size > 0
    assert finite.min() >= 0.0 and finite.max() <= 1.0, (finite.min(), finite.max())
    sig = svf.svf_signature(z)
    assert set(sig) == _SIG_KEYS, set(sig) ^ _SIG_KEYS
    for key, value in sig.items():
        assert type(value) is float, (key, type(value))
    assert sig["svf_p90"] >= sig["svf_p10"], sig
    assert sig["svf_min"] <= sig["svf_median"], sig
    assert 0.0 <= sig["svf_min"] and sig["svf_median"] <= 1.0, sig
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert json.dumps(svf.svf_signature(z)) == dumped          # deterministic


def test_nan_safe():
    # Oracle 5: injected NaN raises nothing; the NaN cells propagate NaN, the
    # rest stays finite and in range, and the signature JSON round-trips.
    z = (synthetic.plane((48, 48), slope_x=0.02)
         + synthetic.rough_field((48, 48), amplitude=1.0, seed=13))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    field = svf.svf_field(z)                                   # must not raise
    assert field.shape == z.shape
    assert np.isnan(field[5, 5]) and np.isnan(field[20, 30]) and np.isnan(field[40, 10])
    good = field[np.isfinite(field)]
    assert good.size > 0
    assert good.min() >= 0.0 and good.max() <= 1.0
    sig = svf.svf_signature(z)                                 # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    for value in sig.values():
        assert type(value) is float
        assert np.isnan(value) or 0.0 <= value <= 1.0, value
    assert json.loads(json.dumps(sig)) is not None
