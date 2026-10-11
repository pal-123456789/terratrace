"""Tests for the swath / transect profile extractor.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring test_slope_area.py /
test_drainage.py.

These exercise a purely GEOMETRIC cross-section / swath extraction of the
sampled height field; nothing here is a process, hydrology, traversability, or
mission claim on any body.
"""
import json

import numpy as np

from terratrace import transect as tr, synthetic

_PROFILE_KEYS = {"distance_m", "elevation", "slope"}
_SWATH_KEYS = {"distance_m", "elev_min", "elev_mean", "elev_max", "elev_std"}
_SIG_KEYS = {"length_m", "relief_m", "max_slope", "mean_slope", "elev_gain_m"}


def test_plane_transect_constant_slope():
    # Oracle 1: a +x planar ramp -> constant slope, strictly monotonic elevation.
    z = synthetic.plane((100, 100), slope_x=0.1, dx=10.0)
    pr = tr.extract_profile(z, (50, 0), (50, 99), dx=10.0)
    assert set(pr) == _PROFILE_KEYS, set(pr)
    assert len(pr["elevation"]) == 100                      # ceil(99)+1 stations
    assert len(pr["slope"]) == len(pr["distance_m"]) == 100
    slope = np.asarray(pr["slope"])
    assert np.all(np.abs(slope - 0.1) <= 0.1 * 0.03)        # ~0.1 within a few %
    elev = np.asarray(pr["elevation"])
    assert np.all(np.diff(elev) > 0.0)                      # strictly monotonic
    sig = tr.transect_signature(z, (50, 0), (50, 99), dx=10.0)
    assert abs(sig["mean_slope"] - 0.1) < 5e-3, sig


def test_flat_tile_zero_relief_and_slope():
    # Oracle 2: a flat tile -> exactly zero relief and zero slope, any transect.
    z = np.zeros((50, 50))
    sig = tr.transect_signature(z, (10, 5), (40, 45), dx=10.0)
    assert sig["relief_m"] == 0.0, sig
    assert sig["max_slope"] == 0.0, sig
    assert sig["elev_gain_m"] == 0.0, sig


def test_swath_envelope_ordering():
    # Oracle 3: on a plane + a ridge, max >= mean >= min elementwise, equal lens.
    z = (synthetic.plane((100, 100), slope_x=0.02, dx=10.0)
         + synthetic.gaussian_hill((100, 100), amplitude=50.0, sigma=12.0, dx=10.0, dy=10.0))
    sw = tr.swath_profile(z, (50, 0), (50, 99), dx=10.0, half_width=4)
    assert set(sw) == _SWATH_KEYS, set(sw)
    lengths = {len(sw[k]) for k in sw}
    assert len(lengths) == 1 and lengths.pop() == len(sw["distance_m"])
    emin = np.asarray(sw["elev_min"])
    emean = np.asarray(sw["elev_mean"])
    emax = np.asarray(sw["elev_max"])
    assert np.all(np.isfinite(emin))                        # interior -> finite
    assert np.all(emax - emean >= -1e-9)
    assert np.all(emean - emin >= -1e-9)


def test_length_correct():
    # Oracle 4: p0=(0,0)->p1=(0,10) at dx=10 spans 100 m.
    z = np.zeros((5, 20))
    sig = tr.transect_signature(z, (0, 0), (0, 10), dx=10.0)
    assert abs(sig["length_m"] - 100.0) < 1e-6, sig


def test_signature_contract():
    # Oracle 5a: keys / types, JSON round-trip, deterministic.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = tr.transect_signature(z, (2, 2), (60, 58), dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    for k in _SIG_KEYS:
        assert type(sig[k]) is float, (k, type(sig[k]))
    dumped = json.dumps(sig)                                # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert json.dumps(tr.transect_signature(z, (2, 2), (60, 58), dx=10.0)) == dumped


def test_nan_safe_and_bounds():
    # Oracle 5b: edge endpoints and a few NaN cells must not raise anywhere.
    z = (synthetic.plane((40, 40), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((40, 40), amplitude=1.5, seed=7))
    z[10, 10] = np.nan
    z[20, 25] = np.nan
    z[0, 0] = np.nan
    pr = tr.extract_profile(z, (0, 0), (0, 39), dx=10.0)     # endpoints on edge
    assert set(pr) == _PROFILE_KEYS
    assert len(pr["elevation"]) == len(pr["slope"]) == len(pr["distance_m"])
    sw = tr.swath_profile(z, (0, 0), (39, 39), dx=10.0, half_width=3)
    assert set(sw) == _SWATH_KEYS
    assert len({len(sw[k]) for k in sw}) == 1
    sig = tr.transect_signature(z, (0, 0), (39, 39), dx=10.0)
    assert set(sig) == _SIG_KEYS
    assert json.loads(json.dumps(sig)) is not None          # NaN stays JSON-safe


def test_offgrid_samples_are_nan():
    # A station outside the grid yields NaN (never raises); in-bounds stay finite.
    z = synthetic.plane((20, 20), slope_x=0.05, dx=5.0)
    pr = tr.extract_profile(z, (10, -5), (10, 25), dx=5.0, n=31)
    elev = np.asarray(pr["elevation"])
    assert np.isnan(elev[0]) and np.isnan(elev[-1])         # off both ends
    assert np.any(np.isfinite(elev))                        # middle on-grid
