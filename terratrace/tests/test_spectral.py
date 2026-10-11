"""Spectral roughness descriptor fixtures (pure NumPy, dependency-free).

Pins the qualitative spectral behaviour of known synthetic surfaces and the
Parseval anchor (summed power ~ detrended variance). No network / challenge data.
"""
import numpy as np

from terratrace import spectral


def test_sinusoid_peak_wavelength():
    # Pure 8-pixel-wavelength tone along x -> dominant wavelength ~ 8 m.
    j = np.arange(64)
    z = np.sin(2 * np.pi * j / 8.0)[None, :] * np.ones((64, 1))
    peak = spectral.spectral_signature(z, dx=1.0)["peak_wavelength_m"]
    assert 6.0 <= peak <= 11.0, peak


def test_white_noise_slope_near_zero():
    z = np.random.default_rng(0).normal(size=(128, 128))
    assert abs(spectral.spectral_slope(z, dx=1.0)) < 1.0


def _smooth(n=128):
    y, x = np.mgrid[0:n, 0:n].astype(float)
    return (np.sin(2 * np.pi * x / 40.0) + 0.8 * np.sin(2 * np.pi * y / 24.0)
            + 0.6 * np.sin(2 * np.pi * (x + y) / 32.0))


def test_smooth_surface_has_negative_slope():
    assert spectral.spectral_slope(_smooth(), dx=1.0) < -1.0


def test_adding_fine_roughness_raises_slope():
    smooth = _smooth()
    noise = np.random.default_rng(7).normal(scale=0.15, size=smooth.shape)
    s_smooth = spectral.spectral_slope(smooth, dx=1.0)
    s_rough = spectral.spectral_slope(smooth + noise, dx=1.0)
    assert s_rough > s_smooth, (s_rough, s_smooth)


def test_parseval_total_power_matches_variance():
    y, x = np.mgrid[0:96, 0:96].astype(float)
    z = np.random.default_rng(3).normal(size=(96, 96)) + 0.01 * x  # mild tilt
    d = spectral.detrend_plane(z)              # same detrend used internally
    var = float(np.var(d))
    tp = spectral.spectral_signature(z, dx=1.0)["total_power"]
    assert abs(tp - var) <= 0.25 * var, (tp, var)


def test_detrend_invariance():
    rng = np.random.default_rng(5)
    y, x = np.mgrid[0:80, 0:80].astype(float)
    z = rng.normal(size=(80, 80)) + np.sin(x / 5.0)
    plane = 12.3 + 0.7 * x - 0.4 * y
    a = spectral.spectral_slope(z, dx=1.0)
    b = spectral.spectral_slope(z + plane, dx=1.0)
    assert abs(a - b) < 1e-6, (a, b)


def test_outputs_finite_and_shaped():
    z = np.random.default_rng(1).normal(size=(100, 100))
    k, psd = spectral.radial_psd(z, dx=2.0)
    assert k.ndim == 1 and psd.ndim == 1 and k.size == psd.size and k.size > 0
    assert np.all(k > 0) and np.all(np.isfinite(psd))
    z2 = z.copy()
    z2[::17, ::13] = np.nan
    k2, psd2 = spectral.radial_psd(z2, dx=2.0)
    assert k2.size > 0 and np.all(np.isfinite(psd2)) and np.all(np.isfinite(k2))


def test_nan_safe():
    rng = np.random.default_rng(2)
    z = rng.normal(size=(100, 100)) + _smooth(100)
    z[rng.random(z.shape) < 0.05] = np.nan
    sig = spectral.spectral_signature(z, dx=1.0)
    assert all(np.isfinite(v) for v in sig.values()), sig
