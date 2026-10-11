"""Tests for the Woodcock (1977) surface-normal orientation-tensor fabric module.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic fabric shapes, mirroring the style of
test_normal_roughness.py / test_slope_area.py.

These exercise a purely GEOMETRIC eigen-analysis of the surface-normal
orientation distribution; nothing here is a process, geologic, traversability,
hazard or mission claim on any body.
"""
import json

import numpy as np

from terratrace import fabric_eigen
from terratrace import synthetic

_SIG_KEYS = {"eig1", "eig2", "eig3", "woodcock_K", "woodcock_C", "isotropy"}


def _corrugation(shape=(80, 80), amp=3.0, wavelength=8.0):
    """A pure 1-D sinusoid ``z = amp*sin(2*pi*j/wavelength)`` (ridges along the
    column axis). The surface is constant along rows, so ``dz/dy == 0`` and every
    normal lies in one vertical (x-z) plane -> an ideal GIRDLE fabric."""
    _, jj = np.indices(shape)
    return amp * np.sin(2.0 * np.pi * jj / float(wavelength))


def test_plane_strong_cluster():
    # Oracle 1: a gentle plane has a single constant normal everywhere, so the
    # orientation cloud is a point/cluster fabric: eig1 ~ 1, eig3 ~ 0, isotropy
    # ~ 0 and a large fabric strength woodcock_C.
    z = synthetic.plane((80, 80), slope_x=0.02, dx=10.0)
    sig = fabric_eigen.fabric_signature(z, dx=10.0)
    assert sig["eig1"] > 0.99, sig
    assert sig["eig3"] < 0.01, sig
    assert sig["isotropy"] < 0.01, sig
    assert np.isfinite(sig["woodcock_C"]) and sig["woodcock_C"] > 3.0, sig


def test_isotropic_rough_field_near_isotropic():
    # Oracle 2: a directionless bumpy field disperses the normals with no
    # preferred axis -> eigenvalues move toward 1/3 each, isotropy is markedly
    # higher than the plane's and the fabric strength woodcock_C is much smaller.
    plane = synthetic.plane((80, 80), slope_x=0.02, dx=10.0)
    rough = synthetic.rough_field((80, 80), amplitude=5.0, seed=3)
    sp = fabric_eigen.fabric_signature(plane, dx=10.0)
    sr = fabric_eigen.fabric_signature(rough)
    assert sr["eig1"] < 0.7, sr                       # no single dominant axis
    assert sr["eig3"] > 0.03, sr                      # smallest axis well off 0
    assert sr["isotropy"] > 0.15, sr                  # near-isotropic normals
    assert sr["isotropy"] > sp["isotropy"], (sr["isotropy"], sp["isotropy"])
    assert sr["woodcock_C"] < 5.0, sr                 # weak preferred orientation
    assert sr["woodcock_C"] < sp["woodcock_C"], (sr["woodcock_C"], sp["woodcock_C"])


def test_corrugation_is_girdle():
    # Oracle 3: a 1-D corrugation -> normals lie in one vertical plane -> GIRDLE,
    # woodcock_K < 1. A PURE 1-D corrugation has dz/dy == 0 exactly, so one
    # eigenvalue (the across-ridge axis) is exactly 0 -> eig3 ~ 0; the girdle
    # shows up as K < 1 and a LARGE second eigenvalue, not in the isotropy.
    z = _corrugation((80, 80), amp=3.0, wavelength=8.0)
    sig = fabric_eigen.fabric_signature(z, dx=1.0)
    assert np.isfinite(sig["woodcock_K"]), sig
    assert sig["woodcock_K"] < 1.0, sig               # girdle, not a cluster
    assert sig["eig3"] < 0.05, sig                    # one near-zero minor axis
    assert sig["eig2"] > 0.2, sig                     # two large axes = girdle


def test_isotropy_ordering():
    # Oracle 3 (companion): rank the three fabrics by isotropy. The cluster
    # (plane) and the ideal 1-D girdle (corrugation) both have a vanishing
    # smallest eigenvalue, so both read isotropy ~ 0 -- the corrugation sits down
    # at the plane's low level, FAR below the directionless bumpy field. (The
    # girdle is told apart from the plane by K < 1 and eig2, not by isotropy.)
    plane = synthetic.plane((80, 80), slope_x=0.02, dx=10.0)
    rough = synthetic.rough_field((80, 80), amplitude=5.0, seed=3)
    corr = _corrugation((80, 80), amp=3.0, wavelength=8.0)
    ip = fabric_eigen.fabric_signature(plane)["isotropy"]
    ir = fabric_eigen.fabric_signature(rough)["isotropy"]
    ic = fabric_eigen.fabric_signature(corr)["isotropy"]
    assert ip < ir, (ip, ir)                          # cluster << isotropic
    assert ic < ir, (ic, ir)                          # girdle  << isotropic
    assert ic < 0.1, ic                               # girdle at the plane's level


def test_orientation_tensor_symmetric_trace_one():
    # The orientation tensor is symmetric, positive semi-definite and has unit
    # trace (each contributing normal is a unit vector).
    z = (synthetic.plane((40, 40), slope_x=0.05, dx=10.0)
         + synthetic.rough_field((40, 40), amplitude=1.0, seed=8))
    t = fabric_eigen.orientation_tensor(z, dx=10.0)
    assert t.shape == (3, 3)
    assert np.all(np.isfinite(t))
    assert np.allclose(t, t.T, atol=1e-12)            # symmetric
    assert abs(float(np.trace(t)) - 1.0) < 1e-9, float(np.trace(t))
    assert np.all(np.linalg.eigvalsh(t) > -1e-9)      # positive semi-definite


def test_signature_contract():
    # Oracle 4: keys/types, ordered eigenvalues summing to 1, JSON-serialisable
    # and deterministic.
    z = synthetic.rough_field((80, 80), amplitude=5.0, seed=3)
    sig = fabric_eigen.fabric_signature(z)
    assert set(sig) == _SIG_KEYS, set(sig)
    for v in sig.values():
        assert type(v) is float, type(v)
    assert sig["eig1"] >= sig["eig2"] >= sig["eig3"] >= 0.0, sig
    assert abs(sig["eig1"] + sig["eig2"] + sig["eig3"] - 1.0) < 1e-9, sig
    assert 0.0 <= sig["isotropy"] <= 1.0, sig
    dumped = json.dumps(sig)                           # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    # deterministic (json token comparison is robust to any NaN values)
    assert json.dumps(fabric_eigen.fabric_signature(z)) == dumped


def test_nan_safe():
    # Oracle 4: a few NaN cells raise nothing in either entry point, and a fully
    # undefined grid yields an all-nan signature instead of an error.
    z = (synthetic.plane((64, 64), slope_x=0.03, dx=10.0)
         + synthetic.rough_field((64, 64), amplitude=2.0, seed=7))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 10] = np.nan
    t = fabric_eigen.orientation_tensor(z, dx=10.0)    # must not raise
    assert t.shape == (3, 3) and np.all(np.isfinite(t))
    sig = fabric_eigen.fabric_signature(z, dx=10.0)    # must not raise
    assert set(sig) == _SIG_KEYS, set(sig)
    assert json.loads(json.dumps(sig)) is not None
    allnan = np.full((16, 16), np.nan)
    bad = fabric_eigen.fabric_signature(allnan)        # no finite normals
    assert set(bad) == _SIG_KEYS, set(bad)
    assert all(np.isnan(v) for v in bad.values()), bad
