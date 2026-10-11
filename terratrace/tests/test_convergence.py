"""Tests for the Koethe & Lehmeier (1996) / Kiss (2004) convergence-index module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_slope_area.py / test_drainage.py.

These exercise a purely GEOMETRIC convergence/divergence measure of the aspect
field of the sampled surface; nothing here is a claim of flow, water, drainage,
or erosion processes on any body.

Sign convention under test (standard geomorphometric definition):
    peak / ridge  -> aspects diverge  -> convergence_mean > 0  (DIVERGENT)
    pit / valley  -> aspects converge -> convergence_mean < 0  (CONVERGENT)
    planar        -> uniform aspect   -> convergence_mean ~ 0
"""
import json

import numpy as np

from terratrace import convergence, synthetic

_SIG_KEYS = {
    "convergence_mean",
    "convergence_median",
    "convergence_std",
    "convergent_fraction",
    "divergent_fraction",
}


def _radial(shape, sign):
    """Radial field centred on the grid: ``sign * hypot(i - c, j - c)``.

    ``sign = -1`` -> a cone (peak at the centre, elevation falling outward in all
    directions) whose aspects point radially OUTWARD; ``sign = +1`` -> a bowl
    (pit at the centre) whose aspects point radially INWARD. Built directly with
    ``np.indices`` so the oracle is analytic.
    """
    rows, cols = shape
    ii, jj = np.indices(shape)
    ci = (rows - 1) / 2.0
    cj = (cols - 1) / 2.0
    r = np.hypot(ii - ci, jj - cj)
    return (sign * r).astype(float)


def test_cone_is_divergent():
    # Oracle 1: a cone (peak at centre) -> aspects fan radially outward ->
    # divergent -> positive convergence index.
    z = _radial((81, 81), sign=-1.0)
    sig = convergence.convergence_signature(z)
    assert np.isfinite(sig["convergence_mean"]), sig
    assert sig["convergence_mean"] > 0.0, sig["convergence_mean"]
    assert sig["divergent_fraction"] > sig["convergent_fraction"], sig


def test_bowl_is_convergent():
    # Oracle 2: a bowl (pit at centre) -> aspects point radially inward ->
    # convergent -> negative convergence index.
    z = _radial((81, 81), sign=1.0)
    sig = convergence.convergence_signature(z)
    assert np.isfinite(sig["convergence_mean"]), sig
    assert sig["convergence_mean"] < 0.0, sig["convergence_mean"]
    assert sig["convergent_fraction"] > sig["divergent_fraction"], sig


def test_plane_near_zero():
    # Oracle 3: a single uniform aspect everywhere averages to exactly 90 deg,
    # so the convergence index of a planar ramp is ~ 0.
    z = synthetic.plane((80, 80), slope_x=0.05, dx=10.0)
    sig = convergence.convergence_signature(z, dx=10.0)
    assert np.isfinite(sig["convergence_mean"]), sig
    assert abs(sig["convergence_mean"]) < 10.0, sig["convergence_mean"]


def test_field_border_is_nan():
    # The one-cell border ring is always NaN; interior cells are finite here.
    z = _radial((40, 40), sign=-1.0)
    field = convergence.convergence_field(z)
    assert field.shape == z.shape
    assert np.all(np.isnan(field[0, :]))
    assert np.all(np.isnan(field[-1, :]))
    assert np.all(np.isnan(field[:, 0]))
    assert np.all(np.isnan(field[:, -1]))
    assert np.any(np.isfinite(field[1:-1, 1:-1]))
    # bounded to [-90, +90] where finite
    fin = field[np.isfinite(field)]
    assert np.all(fin >= -90.0 - 1e-9) and np.all(fin <= 90.0 + 1e-9), fin.min()


def test_signature_contract():
    # Oracle 4: exact keys, float types, JSON round-trip, deterministic.
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=3))
    sig = convergence.convergence_signature(z, dx=10.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    for key in _SIG_KEYS:
        assert type(sig[key]) is float, (key, type(sig[key]))
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(convergence.convergence_signature(z, dx=10.0)) == dumped
    # fractions are genuine fractions in [0, 1]
    assert 0.0 <= sig["convergent_fraction"] <= 1.0, sig
    assert 0.0 <= sig["divergent_fraction"] <= 1.0, sig


def test_nan_safe():
    # Oracle 5: a few NaN cells raise nothing in either entry point.
    z = (synthetic.plane((48, 48), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((48, 48), amplitude=1.5, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    field = convergence.convergence_field(z, dx=10.0)          # must not raise
    assert field.shape == z.shape
    assert np.all(np.isnan(field[0, :])) and np.all(np.isnan(field[-1, :]))
    sig = convergence.convergence_signature(z, dx=10.0)        # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    assert json.loads(json.dumps(sig)) is not None
