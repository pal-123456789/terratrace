"""Tests for the Melton (1965) ruggedness & relief-ratio signature module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_slope_area.py / test_hypsometry.py.

These exercise purely GEOMETRIC tile-scale relief and ruggedness scalars
(Melton 1965; Pike & Wilson 1971); nothing here is a basin-hydrology, hazard,
or mission claim on any body.
"""
import json

import numpy as np

from terratrace import features, melton_relief, synthetic

_SIG_KEYS = {
    "total_relief_m",
    "melton_ruggedness",
    "relief_ratio",
    "elevation_relief_ratio",
}


def test_flat_tile_is_zeros():
    # Oracle 1: a perfectly flat tile has zero relief, so relief and both
    # ratios are exactly 0; the elevation-relief ratio is an undefined 0/0 and
    # is returned as NaN (this module's documented convention, matching
    # features.hypsometric_integral).
    sig = melton_relief.melton_signature(np.zeros((50, 50)))
    assert sig["total_relief_m"] == 0.0, sig
    assert sig["melton_ruggedness"] == 0.0, sig
    assert sig["relief_ratio"] == 0.0, sig
    assert np.isnan(sig["elevation_relief_ratio"]), sig


def test_elevation_relief_tracks_hypsometric_integral():
    # Oracle 2: E = (mean-min)/(max-min) closely approximates the hypsometric
    # integral; it should agree with features.hypsometric_integral to within a
    # small tolerance (the two differ only by E's true min/max vs HI's robust
    # p1/p99 relief band).
    z = (synthetic.plane((64, 64), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=5))
    e = melton_relief.melton_signature(z, dx=10.0)["elevation_relief_ratio"]
    hi = features.hypsometric_integral(z)
    assert np.isfinite(e) and np.isfinite(hi), (e, hi)
    assert abs(e - hi) < 0.05, (e, hi, abs(e - hi))


def test_ruggedness_monotone_in_amplitude():
    # Oracle 3: on the SAME plane and seed, a rougher tile (bigger roughness
    # amplitude) has a larger Melton ruggedness number than a gentler one.
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    gentle = base + synthetic.rough_field((64, 64), amplitude=1.0, seed=11)
    rough = base + synthetic.rough_field((64, 64), amplitude=5.0, seed=11)
    rm_gentle = melton_relief.melton_signature(gentle, dx=10.0)["melton_ruggedness"]
    rm_rough = melton_relief.melton_signature(rough, dx=10.0)["melton_ruggedness"]
    assert rm_rough > rm_gentle, (rm_gentle, rm_rough)


def test_plane_relief_ratio_near_imposed_gradient():
    # Oracle 4 (sanity, loose tol): on a pure planar ramp the relief ratio
    # R_h = H / L is the mean rise-over-run across the tile, so it should sit
    # close to the imposed gradient magnitude slope_x.
    slope_x = 0.1
    z = synthetic.plane((80, 80), slope_x=slope_x, dx=10.0)
    rh = melton_relief.melton_signature(z, dx=10.0)["relief_ratio"]
    assert abs(rh - slope_x) < 0.02, (rh, slope_x)


def test_signature_contract():
    # Oracle 5a: keys/types, in-range, JSON-serialisable, deterministic.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = melton_relief.melton_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    for k in _SIG_KEYS:
        assert type(sig[k]) is float, (k, type(sig[k]))
    assert sig["total_relief_m"] >= 0.0, sig
    assert sig["melton_ruggedness"] >= 0.0, sig
    # On a tile L = sqrt(A), so the Melton number and the relief ratio coincide.
    assert abs(sig["melton_ruggedness"] - sig["relief_ratio"]) < 1e-12, sig
    assert 0.0 <= sig["elevation_relief_ratio"] <= 1.0, sig
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(melton_relief.melton_signature(z, dx=10.0)) == dumped


def test_nan_safe():
    # Oracle 5b: a few NaN cells raise nothing and nodata is dropped cleanly.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    sig = melton_relief.melton_signature(z, dx=10.0)           # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    assert np.isfinite(sig["total_relief_m"])
    assert np.isfinite(sig["melton_ruggedness"])
    assert np.isfinite(sig["relief_ratio"])
    assert json.loads(json.dumps(sig)) is not None
    # all-NaN tile: zeros with E undefined (NaN), still never raises.
    allnan = np.full((16, 16), np.nan)
    s2 = melton_relief.melton_signature(allnan)
    assert s2["total_relief_m"] == 0.0 and s2["melton_ruggedness"] == 0.0
    assert s2["relief_ratio"] == 0.0 and np.isnan(s2["elevation_relief_ratio"])
