"""Tests for the gliding-box lacunarity module (Plotnick, Gardner & O'Neill 1993).

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic/known-ordering answers, mirroring the
style of test_study.py / test_hypsometry.py.
"""
import json

import numpy as np

from terratrace import lacunarity, synthetic


def _clustered_field(n=64, block=4, n_blocks=4, height=100.0, seed=0):
    """A mostly-zero grid with a few tall square blocks -> strongly clustered mass."""
    rng = np.random.default_rng(seed)
    z = np.zeros((n, n), dtype=float)
    for _ in range(n_blocks):
        i = int(rng.integers(0, n - block))
        j = int(rng.integers(0, n - block))
        z[i:i + block, j:j + block] = height
    return z


def test_uniform_lacunarity_one():
    # A perfectly uniform (constant) field: every box carries equal (zero) mass,
    # so Var(S) = 0 and Lambda(r) == 1 exactly at every box size.
    z = np.full((32, 32), 7.0)
    for r in (2, 4, 8):
        lam = lacunarity.gliding_box_lacunarity(z, r)
        assert abs(lam - 1.0) < 1e-9, (r, lam)


def test_clustered_greater_than_uniform():
    # A high-contrast clustered field (sparse tall blocks on zeros) is far gappier
    # than a smooth gradient, so its Lambda(2) is strictly larger.
    clustered = _clustered_field(n=64, block=4, n_blocks=4, height=100.0, seed=1)
    smooth = synthetic.plane((64, 64), slope_x=0.05, slope_y=0.03)
    lam_c = lacunarity.gliding_box_lacunarity(clustered, 2)
    lam_s = lacunarity.gliding_box_lacunarity(smooth, 2)
    assert lam_c > lam_s, (lam_c, lam_s)


def test_lambda_ge_one():
    # Lambda(r) = 1 + Var(S)/Mean(S)^2 is >= 1 by construction, any field / box.
    fields = [
        synthetic.plane((48, 48), slope_x=0.1, slope_y=0.05),
        synthetic.gaussian_hill((48, 48), amplitude=20.0, sigma=6.0),
        synthetic.rough_field((48, 48), amplitude=3.0, seed=1),
        synthetic.rough_field((48, 48), amplitude=1.0, seed=7),
        _clustered_field(n=48, seed=3),
    ]
    for z in fields:
        for r in (2, 4, 8, 16):
            lam = lacunarity.gliding_box_lacunarity(z, r)
            assert np.isfinite(lam), (r, lam)
            assert lam >= 1.0 - 1e-9, (r, lam)


def test_curve_and_signature():
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.02)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=5))
    curve = lacunarity.lacunarity_curve(z, boxes=(2, 4, 8, 16))
    assert sorted(curve.keys()) == [2, 4, 8, 16]
    assert all(type(k) is int for k in curve)
    assert all(type(v) is float and v >= 1.0 - 1e-9 for v in curve.values())

    # Oversized boxes are clipped to the grid's smaller dimension.
    small = synthetic.rough_field((12, 12), amplitude=1.0, seed=2)
    csmall = lacunarity.lacunarity_curve(small, boxes=(2, 4, 8, 16))
    assert max(csmall.keys()) == 12                     # 16 capped to 12
    assert all(k <= 12 for k in csmall)

    sig = lacunarity.lacunarity_signature(z)
    assert set(sig) == {"lacunarity_r2", "lacunarity_mean", "lacunarity_loglog_slope"}
    assert all(type(v) is float for v in sig.values())
    assert np.isfinite(sig["lacunarity_r2"]) and sig["lacunarity_r2"] >= 1.0 - 1e-9
    assert np.isfinite(sig["lacunarity_mean"]) and sig["lacunarity_mean"] >= 1.0 - 1e-9
    assert np.isfinite(sig["lacunarity_loglog_slope"])
    assert abs(sig["lacunarity_r2"] - curve[2]) < 1e-9  # r2 == Lambda(2)
    dumped = json.dumps(sig)                            # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert lacunarity.lacunarity_signature(z) == sig    # deterministic


def test_monotone_decentralize():
    # Lacunarity generally decreases with box size (larger windows average over
    # the clustering), so Lambda(2) >= Lambda(16) for a clustered field.
    z = _clustered_field(n=64, block=4, n_blocks=4, height=100.0, seed=4)
    lam2 = lacunarity.gliding_box_lacunarity(z, 2)
    lam16 = lacunarity.gliding_box_lacunarity(z, 16)
    assert lam2 >= lam16 - 1e-9, (lam2, lam16)


def test_nan_safe():
    z = (synthetic.plane((40, 40), slope_x=0.08, slope_y=0.04)
         + synthetic.rough_field((40, 40), amplitude=1.5, seed=9))
    z[3, 4] = np.nan
    z[10, 20] = np.nan
    z[30, 30] = np.nan
    # Core, curve and signature must all tolerate NaNs and stay finite.
    lam = lacunarity.gliding_box_lacunarity(z, 4)
    assert np.isfinite(lam) and lam >= 1.0 - 1e-9
    curve = lacunarity.lacunarity_curve(z)
    assert curve and all(np.isfinite(v) for v in curve.values())
    sig = lacunarity.lacunarity_signature(z)
    assert all(np.isfinite(v) for v in sig.values())
