"""Tests for topographic openness (dependency-free, assert-based).

Mirrors the plain ``def test_*()`` style used across the suite (e.g.
test_descriptors.py / test_study.py): no pytest, no network, small synthetic
fixtures with analytically known answers. The repo's runner discovers and
calls every top-level ``test_*`` function in this module.
"""
import numpy as np

from terratrace import openness


def _cone(n=21, height=20.0):
    """Flat zeros with a single central cone peaking at the centre cell.

    Returns ``(z, c)`` where ``c = n // 2`` is the centre row/col index. The
    cone descends linearly to 0 at plan radius ``c`` (so its slope per cell is
    constant), which makes the centre an unambiguous local maximum.
    """
    c = n // 2
    yy, xx = np.mgrid[0:n, 0:n]
    dist = np.hypot(xx - c, yy - c)
    z = np.maximum(0.0, height * (1.0 - dist / float(c)))
    return z, c


def test_flat_surface_is_ninety():
    z = np.zeros((20, 20))
    pos = openness.positive_openness(z, radius=5)
    neg = openness.negative_openness(z, radius=5)
    assert pos.shape == z.shape and neg.shape == z.shape
    assert np.max(np.abs(pos - 90.0)) < 1e-6, np.max(np.abs(pos - 90.0))
    assert np.max(np.abs(neg - 90.0)) < 1e-6, np.max(np.abs(neg - 90.0))


def test_peak_has_high_positive_low_negative():
    z, c = _cone(n=21, height=20.0)
    pos = openness.positive_openness(z, radius=10)
    neg = openness.negative_openness(z, radius=10)
    assert pos[c, c] > 90.0, pos[c, c]
    assert neg[c, c] < 90.0, neg[c, c]


def test_pit_is_mirror_of_peak():
    z, c = _cone(n=21, height=20.0)
    z = -z  # central depression
    pos = openness.positive_openness(z, radius=10)
    neg = openness.negative_openness(z, radius=10)
    assert neg[c, c] > 90.0, neg[c, c]
    assert pos[c, c] < 90.0, pos[c, c]


def test_planar_tilt_is_about_ninety():
    n = 24
    z = 0.1 * np.indices((n, n))[1].astype(float)  # z[i, j] = 0.1 * j
    pos = openness.positive_openness(z, radius=5)
    neg = openness.negative_openness(z, radius=5)
    interior = (slice(5, -5), slice(5, -5))
    assert np.max(np.abs(pos[interior] - 90.0)) < 2.0, np.max(np.abs(pos[interior] - 90.0))
    assert np.max(np.abs(neg[interior] - 90.0)) < 2.0, np.max(np.abs(neg[interior] - 90.0))


def test_orientation_equivariant():
    rng = np.random.default_rng(1234)
    z = rng.standard_normal((32, 32))
    r = 6
    base = openness.positive_openness(z, radius=r)
    rotated = openness.positive_openness(np.rot90(z), radius=r)
    interior = (slice(r, -r), slice(r, -r))
    assert np.allclose(rotated[interior], np.rot90(base)[interior],
                       atol=1e-6, rtol=0.0)


def test_range_bounds():
    rng = np.random.default_rng(7)
    z = 3.0 * rng.standard_normal((40, 40))
    pos = openness.positive_openness(z, radius=8)
    neg = openness.negative_openness(z, radius=8)
    for arr in (pos, neg):
        assert np.all(np.isfinite(arr)), "no NaN for a NaN-free input"
        assert arr.min() >= 0.0, arr.min()
        assert arr.max() <= 180.0, arr.max()


def test_nan_safe():
    rng = np.random.default_rng(99)
    z = 2.0 * rng.standard_normal((30, 30))
    z[5, 5] = np.nan
    z[20, 11] = np.nan
    z[13, 27] = np.nan
    result = openness.openness(z, radius=6)  # must not raise
    pos, neg = result["positive"], result["negative"]
    assert pos.shape == z.shape and neg.shape == z.shape
    # The 90.0 fallback for fully-masked cells keeps every output finite.
    assert np.all(np.isfinite(pos)), "positive openness stayed finite"
    assert np.all(np.isfinite(neg)), "negative openness stayed finite"
    # Results away from the inserted nodata cells are ordinary finite angles.
    assert np.isfinite(pos[0, 0]) and np.isfinite(neg[0, 0])


def test_signature_keys_and_types():
    rng = np.random.default_rng(3)
    z = 2.5 * rng.standard_normal((40, 40))
    sig = openness.openness_signature(z, radius=10)
    expected = {"positive_median", "negative_median",
                "positive_p10", "positive_p90", "negative_p10", "negative_p90"}
    assert set(sig) == expected, set(sig) ^ expected
    for key, value in sig.items():
        assert type(value) is float, (key, type(value))
    assert sig["positive_p90"] >= sig["positive_p10"], sig
    assert sig["negative_p90"] >= sig["negative_p10"], sig
