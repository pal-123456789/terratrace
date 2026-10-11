"""Tests for terratrace.tpi_landform -- Weiss (2001) TPI slope-position /
landform classification. Dependency-free: plain ``def test_*()``, assert-based,
no pytest, no network; small synthetic surfaces with analytic answers, mirroring
test_iwahashi_pike.py / test_kh_roughness.py / test_study.py.
"""
import json

import numpy as np

from terratrace import tpi_landform as tp


def _radial(n, sign):
    """Centred radial field on an ``n x n`` grid, with its centre index.

    ``sign=+1`` -> cone (apex HIGH at centre: ``z = dist.max() - dist``);
    ``sign=-1`` -> bowl (centre LOW: ``z = dist``). The flanks are LINEAR in the
    radius so the apex/centre is the one unambiguous local extremum. Returns
    ``(field, (ci, cj))``.
    """
    ci = cj = n // 2
    ii, jj = np.indices((n, n))
    dist = np.hypot(ii - ci, jj - cj).astype(float)
    field = (float(dist.max()) - dist) if sign > 0 else dist
    return field, (ci, cj)


def test_peak_is_ridge():
    cone, (ci, cj) = _radial(81, +1)
    cls = tp.slope_position_classes(cone, dx=1.0, radius=5)
    assert cls[ci, cj] == tp.CLASS_NAMES.index("ridge"), int(cls[ci, cj])


def test_pit_is_valley():
    bowl, (ci, cj) = _radial(81, -1)
    cls = tp.slope_position_classes(bowl, dx=1.0, radius=5)
    assert cls[ci, cj] == tp.CLASS_NAMES.index("valley"), int(cls[ci, cj])


def test_flat_plane_is_flat():
    # Tiny uniform slope (~0.57 deg, well under the 5 deg flat cutoff): the
    # interior TPI is ~0 everywhere, so the plane is dominantly 'flat'.
    jj = np.indices((80, 80))[1].astype(float)
    plane = 0.01 * jj
    sig = tp.tpi_landform_signature(plane, dx=1.0, radius=5)
    comp = sig["composition"]
    assert sig["dominant_class"] == "flat", sig
    assert comp["flat"] == max(comp.values()), comp
    assert comp["flat"] > 0.5, comp


def test_composition_sums_to_one():
    cone, _ = _radial(72, +1)
    rng = np.random.default_rng(7)
    field = cone + rng.normal(0.0, 0.3, cone.shape)
    sig = tp.tpi_landform_signature(field, dx=1.0, radius=5)
    comp = sig["composition"]
    assert set(comp) == set(tp.CLASS_NAMES)
    assert abs(sum(comp.values()) - 1.0) < 1e-9, sum(comp.values())
    assert all(0.0 <= v <= 1.0 for v in comp.values())
    assert sig["dominant_class"] in tp.CLASS_NAMES
    assert json.loads(json.dumps(sig))                               # serialisable
    assert tp.tpi_landform_signature(field, dx=1.0, radius=5) == sig  # deterministic


def test_classes_shape_sentinel():
    rng = np.random.default_rng(3)
    z = rng.normal(0.0, 1.0, (50, 50))
    z[10, 12] = np.nan
    z[30, 5] = np.nan
    cls = tp.slope_position_classes(z, dx=1.0, radius=4)
    assert cls.shape == z.shape
    assert cls.dtype == np.int8
    assert int(cls[10, 12]) == -1 and int(cls[30, 5]) == -1   # NaN cells -> -1
    valid = cls[cls >= 0]
    assert valid.size and int(valid.min()) >= 0 and int(valid.max()) <= 5


def test_nan_safe():
    cone, _ = _radial(48, +1)
    cone[5, 5] = np.nan
    cone[20, 30] = np.nan
    cone[0, 0] = np.nan
    t = tp.tpi(cone, dx=1.0, radius=5)                     # must not raise
    cls = tp.slope_position_classes(cone, dx=1.0, radius=5)
    sig = tp.tpi_landform_signature(cone, dx=1.0, radius=5)
    assert t.shape == cone.shape and np.isnan(t[5, 5])
    assert int(cls[5, 5]) == -1
    assert set(sig["composition"]) == set(tp.CLASS_NAMES)
