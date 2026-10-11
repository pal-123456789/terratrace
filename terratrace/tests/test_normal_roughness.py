"""Tests for the surface-normal dispersion roughness (vector strength), after
Hobson (1972) / McKean & Roering (2004). Dependency-free: plain ``def test_*()``,
assert-based, no pytest, no network -- small synthetic surfaces with analytic or
monotone-by-construction answers, mirroring the style of test_kh_roughness.py /
test_descriptors.py.
"""
import json

import numpy as np

from terratrace import normal_roughness as nr
from terratrace import synthetic


def _gentle_sinusoid(shape=(96, 96), dx=10.0, amp=2.0, wavelength=240.0):
    """A smooth, long-wavelength ripple: gentle gradients -> nearly aligned
    normals -> low dispersion roughness."""
    rows, cols = shape
    i, j = np.indices(shape)
    x = j * dx
    y = i * dx
    return amp * (np.sin(2.0 * np.pi * x / wavelength)
                  + np.cos(2.0 * np.pi * y / wavelength))


def test_plane_zero_roughness():
    # A tilted plane has a single constant normal everywhere, so the resultant
    # vector strength R == 1 and roughness == 1 - R == 0 in every window.
    z = synthetic.plane((80, 80), slope_x=0.3, slope_y=0.15, dx=5.0)
    r = nr.normal_roughness(z, dx=5.0, window=5)
    assert np.all(np.isfinite(r))
    assert float(np.max(np.abs(r))) < 1e-6, float(np.max(np.abs(r)))


def test_rough_greater_than_smooth():
    rough = synthetic.rough_field((96, 96), amplitude=3.0, seed=1)
    smooth = _gentle_sinusoid((96, 96), dx=10.0, amp=2.0, wavelength=240.0)
    r_rough = nr.normal_roughness_signature(rough, dx=10.0)["roughness_mean"]
    r_smooth = nr.normal_roughness_signature(smooth, dx=10.0)["roughness_mean"]
    assert np.isfinite(r_rough) and np.isfinite(r_smooth)
    assert r_rough > r_smooth, (r_rough, r_smooth)


def test_bounds():
    z = (synthetic.plane((72, 72), slope_x=0.05, dx=10.0)
         + synthetic.rough_field((72, 72), amplitude=1.5, seed=4))
    r = nr.normal_roughness(z, dx=10.0, window=5)
    assert np.all(np.isfinite(r))                      # clean grid -> no NaN cells
    assert float(np.min(r)) >= 0.0 and float(np.max(r)) <= 1.0, (float(np.min(r)), float(np.max(r)))
    sig = nr.normal_roughness_signature(z, dx=10.0)
    assert set(sig) == {"roughness_mean", "roughness_median", "roughness_p90"}, set(sig)
    for v in sig.values():
        assert type(v) is float, type(v)
        assert 0.0 <= v <= 1.0, v
    dumped = json.dumps(sig)                            # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped)
    assert nr.normal_roughness_signature(z, dx=10.0) == sig  # deterministic


def test_monotone_amplitude():
    # Scaling the same seeded field up (steeper, more dispersed normals) must
    # raise the mean roughness monotonically.
    amps = [0.5, 1.5, 4.5]
    means = [nr.normal_roughness_signature(
                 synthetic.rough_field((96, 96), amplitude=a, seed=11))["roughness_mean"]
             for a in amps]
    assert all(np.isfinite(m) for m in means), means
    assert all(means[i] < means[i + 1] for i in range(len(means) - 1)), means


def test_nan_safe():
    z = (synthetic.plane((64, 64), slope_x=0.04, dx=8.0)
         + synthetic.rough_field((64, 64), amplitude=1.0, seed=5))
    z[10, 10] = np.nan
    z[25, 30] = np.nan
    z[40, 5] = np.nan
    r = nr.normal_roughness(z, dx=8.0, window=5)        # a few NaNs -> no raise
    assert np.isfinite(r).any()                         # finite elsewhere
    assert np.isfinite(r[55, 55])                        # far from every NaN
    sig = nr.normal_roughness_signature(z, dx=8.0)
    assert np.isfinite(sig["roughness_mean"])
    assert json.loads(json.dumps(sig))


def test_normals_unit():
    z = (synthetic.gaussian_hill((50, 50), amplitude=8.0, sigma=6.0, dx=5.0)
         + synthetic.rough_field((50, 50), amplitude=0.5, seed=2))
    nx, ny, nz = nr.surface_normals(z, dx=5.0)
    mag2 = nx * nx + ny * ny + nz * nz
    finite = np.isfinite(mag2)
    assert finite.all()                                  # clean grid -> all defined
    assert np.allclose(mag2[finite], 1.0, atol=1e-10), float(np.max(np.abs(mag2[finite] - 1.0)))
    assert np.all(nz[finite] > 0.0)                      # normals point up
