"""Tests for the directional terrain-fabric (anisotropy) analyzer.

Dependency-free, assert-based, matching the house style (plain ``def test_*()``,
no pytest, no network, small synthetic fixtures with analytically known fabric).
The repo runner discovers and calls every top-level ``test_*`` in this module.

Fabric convention under test: ``orientation_deg`` is the azimuth of MINIMUM
directional roughness (the along-ridge / lineation strike), with 0 deg = +x
(east, columns) and 90 deg = +y (north, rows); azimuths bin over [0, 180).
"""
import numpy as np

from terratrace import anisotropy


def _x_ridges(n=96, wavelength=12.0):
    """z[i, j] = sin(2*pi*j / wavelength): elevation varies with the COLUMN
    index (x) and is constant along ROWS (y), so the ridge crests run along y."""
    row = np.sin(2.0 * np.pi * np.arange(n) / wavelength)
    return np.tile(row, (n, 1))


def test_x_ridges_oriented_along_y():
    z = _x_ridges(96, 12.0)
    a = anisotropy.anisotropy(z)
    # Strongly lineated -> high anisotropy strength.
    assert a["strength"] > 0.5, a["strength"]
    # Orientation is the low-roughness (along-ridge) direction ~ 90 degrees.
    assert abs(a["orientation_deg"] - 90.0) <= 25.0, a["orientation_deg"]
    # Across the ridges (~0 deg) is rougher than along them (~90 deg).
    az, rough = anisotropy.directional_roughness(z)
    r_across = rough[int(np.argmin(np.abs(az - 0.0)))]
    r_along = rough[int(np.argmin(np.abs(az - 90.0)))]
    assert r_across > r_along, (r_across, r_along)


def test_y_ridges_is_transpose():
    # Transpose of case 1: ridges now run along x -> strike ~ 0 (or 180).
    z2 = _x_ridges(96, 12.0).T
    a = anisotropy.anisotropy(z2)
    assert a["strength"] > 0.5, a["strength"]
    o = a["orientation_deg"]
    assert min(abs(o - 0.0), abs(o - 180.0)) <= 25.0, o


def test_isotropic_noise_low_strength():
    z = np.random.default_rng(0).normal(size=(96, 96))
    a = anisotropy.anisotropy(z)
    assert a["strength"] < 0.25, a["strength"]


def test_strength_bounds():
    ii, jj = np.indices((64, 64))
    surfaces = [
        _x_ridges(64, 10.0),                       # strongly lineated
        np.random.default_rng(3).normal(size=(64, 64)),  # isotropic noise
        0.1 * jj + 0.05 * ii,                      # tilted plane (directional, finite)
        np.full((40, 40), 5.0),                    # perfectly flat (degenerate path)
    ]
    for z in surfaces:
        a = anisotropy.anisotropy(z)
        assert 0.0 <= a["strength"] <= 1.0, a["strength"]
        assert 0.0 <= a["isotropy"] <= 1.0, a["isotropy"]


def test_constant_offset_invariance():
    z = _x_ridges(96, 12.0)
    base = anisotropy.anisotropy(z)
    shifted = anisotropy.anisotropy(z + 100.0)   # vertical datum offset
    assert abs(base["strength"] - shifted["strength"]) < 1e-9, (
        base["strength"], shifted["strength"])
    assert abs(base["orientation_deg"] - shifted["orientation_deg"]) < 1e-9, (
        base["orientation_deg"], shifted["orientation_deg"])


def test_signature_keys_and_types():
    z = _x_ridges(64, 10.0) + 0.1 * np.random.default_rng(1).normal(size=(64, 64))
    sig = anisotropy.anisotropy_signature(z)
    expected = {"strength", "orientation_deg", "isotropy", "mean_roughness"}
    assert set(sig) == expected, set(sig) ^ expected
    for key, value in sig.items():
        assert type(value) is float, (key, type(value))


def test_nan_safe():
    rng = np.random.default_rng(7)
    z = rng.normal(size=(96, 96))
    z[rng.random((96, 96)) < 0.05] = np.nan   # ~5% nodata
    a = anisotropy.anisotropy(z)              # must not raise
    assert np.isfinite(a["strength"]), a["strength"]
    assert 0.0 <= a["strength"] <= 1.0, a["strength"]


def test_directional_roughness_shapes():
    z = np.random.default_rng(2).normal(size=(50, 50))
    for n_dirs in (8, 4, 12):
        az, rough = anisotropy.directional_roughness(z, n_dirs=n_dirs)
        assert az.shape == (n_dirs,) and rough.shape == (n_dirs,), (az.shape, rough.shape)
        assert len(az) == len(rough) == n_dirs
        assert np.all(az >= 0.0) and np.all(az < 180.0), az
