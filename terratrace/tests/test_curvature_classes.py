"""Tests for terratrace.curvature_classes -- Wood (1996) / Dikau (1989)
morphometric curvature-feature classification (peak / pit / ridge / channel /
pass / planar). Dependency-free: plain ``def test_*()``, assert-based, no pytest,
no network; small synthetic quadratics with analytic answers, mirroring the style
of test_tpi_landform.py / test_slope_area.py.

These exercise a purely GEOMETRIC curvature-sign SHAPE classification of the
sampled surface; nothing here is a geological-unit, process, hazard, or mission
claim on any body.
"""
import json

import numpy as np

from terratrace import curvature_classes as cc, synthetic

_SIX = {"planar", "peak", "pit", "ridge", "channel", "pass"}


def _quad(n, kind):
    """Centred analytic quadratic on an ``n x n`` grid; returns (field, (ci, cj)).

    ``X = j - c``, ``Y = i - c`` with ``c = n // 2``:
      dome    z = -(X^2 + Y^2)   convex up  -> centre 'peak'
      bowl    z =  (X^2 + Y^2)   concave up -> centre 'pit'
      saddle  z =  X^2 - Y^2     saddle     -> centre 'pass'
      ridge   z = -(X^2)         convex along x, straight along y -> 'ridge'
      channel z =  (X^2)         concave along x, straight along y -> 'channel'
    """
    c = n // 2
    ii, jj = np.indices((n, n))
    x = (jj - c).astype(float)
    y = (ii - c).astype(float)
    fields = {
        "dome": -(x ** 2 + y ** 2),
        "bowl": (x ** 2 + y ** 2),
        "saddle": x ** 2 - y ** 2,
        "ridge": -(x ** 2),
        "channel": (x ** 2),
    }
    return fields[kind], (c, c)


def test_dome_centre_is_peak():
    dome, (ci, cj) = _quad(81, "dome")
    m = cc.curvature_class_map(dome)
    assert cc.CODE_TO_NAME.get(int(m[ci, cj])) == "peak", int(m[ci, cj])
    assert cc.curvature_class_signature(dome)["dominant_class"] == "peak"


def test_bowl_centre_is_pit():
    bowl, (ci, cj) = _quad(81, "bowl")
    m = cc.curvature_class_map(bowl)
    assert cc.CODE_TO_NAME.get(int(m[ci, cj])) == "pit", int(m[ci, cj])
    assert cc.curvature_class_signature(bowl)["dominant_class"] == "pit"


def test_saddle_centre_is_pass():
    saddle, (ci, cj) = _quad(81, "saddle")
    m = cc.curvature_class_map(saddle)
    assert cc.CODE_TO_NAME.get(int(m[ci, cj])) == "pass", int(m[ci, cj])


def test_ridge_and_channel():
    ridge, _ = _quad(81, "ridge")
    channel, _ = _quad(81, "channel")
    assert cc.curvature_class_signature(ridge)["dominant_class"] == "ridge"
    assert cc.curvature_class_signature(channel)["dominant_class"] == "channel"


def test_plane_dominant_planar():
    pl = synthetic.plane((80, 80), slope_x=0.03, dx=10.0)
    sig = cc.curvature_class_signature(pl, dx=10.0)
    assert sig["dominant_class"] == "planar", sig
    # a tilted plane has zero curvature everywhere -> essentially all planar
    assert sig["composition"]["planar"] > 0.95, sig


def test_principal_curvature_signs():
    dome, (ci, cj) = _quad(81, "dome")
    saddle, _ = _quad(81, "saddle")
    k1, k2 = cc.principal_curvatures(dome)
    # dome centre: both principal curvatures convex (+) and ~equal (+2)
    assert k1[ci - 1, cj - 1] > 0.0 and k2[ci - 1, cj - 1] > 0.0
    assert abs(float(k1[ci - 1, cj - 1]) - 2.0) < 1e-9
    s1, s2 = cc.principal_curvatures(saddle)
    # saddle: opposite-sign principal curvatures everywhere interior (+2, -2)
    assert np.nanmax(s1) > 0.0 and np.nanmin(s2) < 0.0
    assert np.all(s1[np.isfinite(s1)] >= s2[np.isfinite(s2)] - 1e-9)


def test_signature_contract():
    rng = np.random.default_rng(11)
    dome, _ = _quad(72, "dome")
    z = dome + rng.normal(0.0, 0.5, dome.shape)
    sig = cc.curvature_class_signature(z, dx=1.0)
    comp = sig["composition"]
    assert set(comp) == _SIX == set(cc.CLASS_NAMES)
    assert all(type(v) is float for v in comp.values())
    assert abs(sum(comp.values()) - 1.0) < 1e-9, sum(comp.values())
    assert all(0.0 <= v <= 1.0 for v in comp.values())
    assert sig["dominant_class"] in _SIX
    dumped = json.dumps(sig)                                   # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped) is not None
    assert json.dumps(cc.curvature_class_signature(z, dx=1.0)) == dumped  # deterministic


def test_map_shape_sentinel():
    z, _ = _quad(50, "dome")
    m = cc.curvature_class_map(z)
    assert m.shape == z.shape
    assert m.dtype == np.int8
    assert np.all(m[0, :] == -1) and np.all(m[-1, :] == -1)    # border sentinel
    assert np.all(m[:, 0] == -1) and np.all(m[:, -1] == -1)
    valid = m[m >= 0]
    assert valid.size and int(valid.min()) >= 0 and int(valid.max()) <= 5


def test_nan_safe():
    dome, _ = _quad(48, "dome")
    dome[5, 5] = np.nan
    dome[20, 30] = np.nan
    dome[0, 0] = np.nan
    k1, k2 = cc.principal_curvatures(dome)                     # must not raise
    m = cc.curvature_class_map(dome)                           # must not raise
    sig = cc.curvature_class_signature(dome)                   # must not raise
    assert k1.shape == (46, 46) and np.isnan(k1[4, 4])         # NaN propagates
    assert int(m[5, 5]) == -1 and int(m[20, 30]) == -1
    assert set(sig["composition"]) == _SIX
    assert json.loads(json.dumps(sig)) is not None
