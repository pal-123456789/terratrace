"""Tests for the Kreslavsky & Head (2000) differential-slope baseline roughness
(gridded adaptation). Dependency-free: plain ``def test_*()``, assert-based, no
pytest, no network -- small synthetic surfaces with analytic answers, mirroring
the style of test_descriptors.py / test_features.py.
"""
import json
import math

import numpy as np

from terratrace import kh_roughness, synthetic


def test_plane_is_zero():
    # The second difference of a linear field is identically zero, so a tilted
    # plane has exactly zero differential-slope roughness at any baseline.
    z = synthetic.plane((60, 60), slope_x=0.3, slope_y=0.15, dx=5.0)
    r = kh_roughness.baseline_roughness(z, dx=5.0, baseline_m=20.0)
    assert np.isfinite(r)
    assert r < 1e-9, r


def test_quadratic_analytic():
    # z = q*(X^2 + Y^2) with X=j*dx, Y=i*dx. The second difference of a quadratic
    # is constant, so the differential slope is a CONSTANT degrees(arctan(2*q*k*dx))
    # at half-baseline k (identical along x and y) -> the pooled median equals it.
    shape, dx, q, baseline = (70, 70), 4.0, 0.001, 24.0
    i, j = np.indices(shape)
    X = j * dx
    Y = i * dx
    z = q * (X ** 2 + Y ** 2)
    k = kh_roughness.half_baseline_cells(dx, baseline)      # k exactly as the module derives it
    expected = math.degrees(math.atan(2.0 * q * k * dx))

    dsx, dsy = kh_roughness.differential_slope(z, dx=dx, baseline_m=baseline)
    fx = dsx[np.isfinite(dsx)]
    fy = dsy[np.isfinite(dsy)]
    assert fx.size > 0 and fy.size > 0
    # the differential slope is a single constant over the whole valid interior
    assert float(np.std(fx)) < 1e-6, float(np.std(fx))
    assert float(np.std(fy)) < 1e-6, float(np.std(fy))

    r = kh_roughness.baseline_roughness(z, dx=dx, baseline_m=baseline)
    assert abs(r - expected) < 1e-6, (r, expected, k)


def test_noise_greater_than_smooth():
    base = synthetic.plane((80, 80), slope_x=0.05, dx=10.0)
    smooth = base + synthetic.rough_field((80, 80), amplitude=0.1, seed=1)
    rough = base + synthetic.rough_field((80, 80), amplitude=3.0, seed=1)
    r_smooth = kh_roughness.baseline_roughness(smooth, dx=10.0, baseline_m=40.0)
    r_rough = kh_roughness.baseline_roughness(rough, dx=10.0, baseline_m=40.0)
    assert np.isfinite(r_smooth) and np.isfinite(r_rough)
    assert r_rough > r_smooth, (r_rough, r_smooth)


def test_monotone_amplitude():
    base = synthetic.plane((80, 80), slope_x=0.02, dx=10.0)
    amps = [0.25, 1.0, 4.0]
    seq = [kh_roughness.baseline_roughness(
               base + synthetic.rough_field((80, 80), amplitude=a, seed=7),
               dx=10.0, baseline_m=40.0)
           for a in amps]
    assert all(np.isfinite(s) for s in seq), seq
    assert all(seq[i] < seq[i + 1] for i in range(len(seq) - 1)), seq


def test_profile_and_signature():
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=5.0)
         + synthetic.rough_field((64, 64), amplitude=1.0, seed=3))
    prof = kh_roughness.roughness_profile(z, dx=5.0, baselines_m=[10.0, 20.0, 40.0])
    keys = list(prof)
    assert keys == sorted(keys), keys                        # ascending baselines
    assert all(type(k) is float for k in keys)
    assert all(np.isfinite(v) and type(v) is float for v in prof.values()), prof

    sig = kh_roughness.kh_roughness_signature(z, dx=5.0)
    assert set(sig) == {"baseline_roughness_fine", "baseline_roughness_coarse",
                        "profile", "profile_loglog_slope"}, set(sig)
    for key in ("baseline_roughness_fine", "baseline_roughness_coarse",
                "profile_loglog_slope"):
        assert type(sig[key]) is float, (key, type(sig[key]))
    assert isinstance(sig["profile"], dict) and sig["profile"]
    assert all(type(k) is float for k in sig["profile"])
    assert all(type(v) is float for v in sig["profile"].values())
    assert np.isfinite(sig["baseline_roughness_fine"])
    assert np.isfinite(sig["baseline_roughness_coarse"])
    assert np.isfinite(sig["profile_loglog_slope"]), sig  # 3 default baselines -> defined
    dumped = json.dumps(sig)                                 # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped)
    assert kh_roughness.kh_roughness_signature(z, dx=5.0) == sig  # deterministic


def test_nan_safe():
    z = (synthetic.plane((50, 50), slope_x=0.04, dx=8.0)
         + synthetic.rough_field((50, 50), amplitude=1.0, seed=5))
    z[10, 10] = np.nan
    z[25, 30] = np.nan
    z[40, 5] = np.nan
    r = kh_roughness.baseline_roughness(z, dx=8.0, baseline_m=32.0)
    assert np.isfinite(r), r                                 # a few NaNs -> no raise, finite
    sig = kh_roughness.kh_roughness_signature(z, dx=8.0)
    assert np.isfinite(sig["baseline_roughness_fine"])
    assert json.loads(json.dumps(sig))
