"""Geomorphon fixtures (dependency-free; plain asserts, no pytest).

Validates the ternary line-of-sight signature and the explicit antisymmetric
10-class reduction against canonical synthetic landforms with known shapes.
"""
import numpy as np

from terratrace import geomorphons as gm


# Antisymmetric partner of each form under swapping n_plus <-> n_minus.
_SWAP = {
    "flat": "flat", "slope": "slope",
    "peak": "pit", "pit": "peak",
    "ridge": "valley", "valley": "ridge",
    "shoulder": "footslope", "footslope": "shoulder",
    "spur": "hollow", "hollow": "spur",
}


def test_classify_form_canonical():
    cases = {
        (0, 0): "flat", (8, 0): "peak", (0, 8): "pit",
        (6, 0): "ridge", (0, 6): "valley", (3, 0): "shoulder",
        (0, 3): "footslope", (3, 3): "slope", (4, 1): "spur", (1, 4): "hollow",
    }
    for (p, m), name in cases.items():
        got = gm.classify_form(p, m)
        assert got == name, ((p, m), got, name)


def test_classify_form_antisymmetry():
    for p in range(9):
        for m in range(9):
            if p + m > 8:
                continue
            a = gm.classify_form(p, m)
            b = gm.classify_form(m, p)
            assert b == _SWAP[a], ((p, m), a, b)


def test_flat_plane_all_flat():
    z = np.zeros((24, 24))
    comp = gm.composition(z)
    assert comp["flat"] > 0.95, comp
    n_plus, n_minus = gm.ternary_counts(z)
    inner = (slice(4, 20), slice(4, 20))
    assert np.all(n_plus[inner] == 0) and np.all(n_minus[inner] == 0)
def test_cone_apex_is_peak():
    n, c = 41, 20
    i, j = np.indices((n, n))
    z = -np.hypot(i - c, j - c).astype(float)   # apex high at the centre
    codes = gm.landforms(z, search=8)
    assert codes[c, c] == gm.FORM_NAMES.index("peak"), int(codes[c, c])


def test_bowl_center_is_pit():
    n, c = 41, 20
    i, j = np.indices((n, n))
    z = np.hypot(i - c, j - c).astype(float)    # centre low
    codes = gm.landforms(z, search=8)
    assert codes[c, c] == gm.FORM_NAMES.index("pit"), int(codes[c, c])


def test_planar_tilt_is_slope():
    i, j = np.indices((40, 40))
    z = 0.2 * j.astype(float)
    sig = gm.geomorphon_signature(z)
    assert sig["dominant_form"] == "slope", sig["dominant_form"]


def test_tent_ridge_is_ridge():
    n, c = 41, 20
    i, j = np.indices((n, n))
    z = -np.abs(j - c).astype(float)            # tent crest along the i-axis
    codes = gm.landforms(z, search=8)
    assert codes[c, c] == gm.FORM_NAMES.index("ridge"), int(codes[c, c])


def test_tent_valley_is_valley():
    n, c = 41, 20
    i, j = np.indices((n, n))
    z = np.abs(j - c).astype(float)             # tent trough along the i-axis
    codes = gm.landforms(z, search=8)
    assert codes[c, c] == gm.FORM_NAMES.index("valley"), int(codes[c, c])


def test_relief_invariance():
    # Integer-valued surface -> (z + 100) subtraction is exact in float, so the
    # relief-invariance holds bit-for-bit regardless of flatness-boundary cases.
    rng = np.random.default_rng(7)
    z = rng.integers(-20, 21, size=(30, 30)).astype(float)
    a = gm.composition(z)
    b = gm.composition(z + 100.0)
    assert set(a) == set(b)
    for k in a:
        assert abs(a[k] - b[k]) < 1e-9, (k, a[k], b[k])


def test_orientation_consistency():
    rng = np.random.default_rng(11)
    z = rng.standard_normal((30, 30)) * 4.0
    a = sorted(gm.composition(z).items())
    b = sorted(gm.composition(np.rot90(z)).items())
    assert [k for k, _ in a] == [k for k, _ in b]
    for (ka, va), (kb, vb) in zip(a, b):
        assert ka == kb and abs(va - vb) < 1e-9, (ka, va, vb)


def test_spectrum_shape_and_sum():
    rng = np.random.default_rng(3)
    z = rng.standard_normal((32, 32)) * 5.0
    spec = gm.spectrum(z)
    assert spec.shape == (9, 9)
    assert abs(float(spec.sum()) - 1.0) < 1e-9, float(spec.sum())


def test_signature_contract():
    rng = np.random.default_rng(5)
    z = rng.standard_normal((28, 28)) * 3.0
    sig = gm.geomorphon_signature(z)
    for key in ("composition", "spectrum", "dominant_form"):
        assert key in sig, key
    assert abs(sum(sig["composition"].values()) - 1.0) < 1e-9
    assert sig["dominant_form"] in gm.FORM_NAMES
    spec = sig["spectrum"]
    assert isinstance(spec, list) and len(spec) == 9
    assert all(isinstance(row, list) and len(row) == 9 for row in spec)

