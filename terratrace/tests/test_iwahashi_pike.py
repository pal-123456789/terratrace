"""Tests for the Iwahashi & Pike (2007) three-part geometric signature +
first-level nested-means terrain classification. Dependency-free: plain
``def test_*()``, assert-based, no pytest, no network -- small synthetic
surfaces with analytic answers, mirroring test_kh_roughness.py /
test_descriptors.py.
"""
import json
import time

import numpy as np

from terratrace import iwahashi_pike as ip, synthetic


def _radial(shape, sign):
    """Radial field centred on the grid: ``sign=-1`` -> dome (apex high, z=-r);
    ``sign=+1`` -> basin (centre low, z=+r). Returns ``(field, (ci, cj))``."""
    ci, cj = shape[0] // 2, shape[1] // 2
    ii, jj = np.indices(shape)
    return sign * np.hypot(ii - ci, jj - cj).astype(float), (ci, cj)


def test_convexity_bounds_dome_high_basin_low():
    dome, (ci, cj) = _radial((80, 80), -1.0)
    basin, _ = _radial((80, 80), 1.0)
    cv_d = ip.local_convexity(dome)
    cv_b = ip.local_convexity(basin)
    assert cv_d.shape == dome.shape
    # bounded in [0, 100] over the finite cells
    for cv in (cv_d, cv_b):
        fin = cv[np.isfinite(cv)]
        assert fin.size and float(fin.min()) >= 0.0 and float(fin.max()) <= 100.0
    # a dome is convex at its centre; a basin is not
    assert float(cv_d[ci, cj]) > float(cv_b[ci, cj])
    assert float(cv_d[ci, cj]) > 90.0 and float(cv_b[ci, cj]) < 10.0


def test_texture_rough_vs_smooth():
    plane = synthetic.plane((80, 80), slope_x=0.02, dx=1.0)
    rough = plane + synthetic.rough_field((80, 80), amplitude=2.0, seed=101)
    t_smooth = float(np.nanmean(ip.surface_texture(plane)))
    t_rough = float(np.nanmean(ip.surface_texture(rough)))
    assert t_smooth < 1e-6, t_smooth            # smooth plane residual ~ 0
    assert t_rough > t_smooth, (t_rough, t_smooth)
    assert t_rough > 10.0, t_rough              # decisively textured

def test_plane_mostly_one_class_composition_valid():
    plane = synthetic.plane((70, 70), slope_x=0.1, slope_y=0.05, dx=1.0)
    comp = ip.terrain_class_composition(plane)
    assert set(comp) == {str(c) for c in range(8)}
    assert abs(sum(comp.values()) - 1.0) < 1e-9, sum(comp.values())
    assert all(0.0 <= v <= 1.0 for v in comp.values())
    assert max(comp.values()) > 0.95, comp      # homogeneous surface -> one class


def test_classes_shape_and_nan_sentinel():
    z = (synthetic.plane((50, 50), slope_x=0.05, dx=1.0)
         + synthetic.rough_field((50, 50), amplitude=1.0, seed=5))
    z[10, 12] = np.nan
    z[30, 5] = np.nan
    cls = ip.nested_means_classes(z)
    assert cls.shape == z.shape
    assert cls.dtype == np.int8
    assert int(cls[10, 12]) == -1 and int(cls[30, 5]) == -1   # NaN cells -> -1
    valid = cls[cls >= 0]
    assert valid.size and int(valid.min()) >= 0 and int(valid.max()) <= 7


def test_signature_contract_json_and_dominant_class():
    z = (synthetic.plane((64, 64), slope_x=0.03, slope_y=0.01, dx=1.0)
         + synthetic.rough_field((64, 64), amplitude=1.2, seed=7))
    sig = ip.iwahashi_pike_signature(z, dx=1.0)
    assert set(sig) == {"slope_mean", "convexity_mean", "texture_mean",
                        "composition", "dominant_class"}, set(sig)
    for key in ("slope_mean", "convexity_mean", "texture_mean"):
        assert type(sig[key]) is float and np.isfinite(sig[key]), key
    comp = sig["composition"]
    assert set(comp) == {str(c) for c in range(8)}
    assert abs(sum(comp.values()) - 1.0) < 1e-9
    assert type(sig["dominant_class"]) is int and 0 <= sig["dominant_class"] <= 7
    assert sig["dominant_class"] == max(range(8), key=lambda c: comp[str(c)])
    dumped = json.dumps(sig)                                  # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped)
    assert ip.iwahashi_pike_signature(z, dx=1.0) == sig       # deterministic


def test_geometric_signature_means_plane_vs_rough():
    plane = synthetic.plane((48, 48), slope_x=0.1, dx=1.0)
    rough = plane + synthetic.rough_field((48, 48), amplitude=1.5, seed=11)
    gs_p = ip.geometric_signature(plane)
    gs_r = ip.geometric_signature(rough)
    assert set(gs_p) == {"slope_mean", "convexity_mean", "texture_mean"}
    assert all(type(v) is float for v in gs_p.values())
    assert gs_p["texture_mean"] < 1e-6, gs_p                  # plane ~ no texture
    assert gs_r["texture_mean"] > gs_p["texture_mean"], (gs_r, gs_p)

def test_window_must_be_odd():
    z = synthetic.plane((20, 20), slope_x=0.1, dx=1.0)
    for bad in (2, 4, 10):
        try:
            ip.local_convexity(z, window=bad)
        except ValueError:
            pass
        else:
            raise AssertionError(f"even window {bad} should raise ValueError")


def test_nan_safe_and_timing_96():
    z = (synthetic.plane((96, 96), slope_x=0.03, dx=1.0)
         + synthetic.rough_field((96, 96), amplitude=1.0, seed=9))
    z[5, 5] = np.nan
    z[50, 70] = np.nan
    t0 = time.perf_counter()
    sig = ip.iwahashi_pike_signature(z, dx=1.0)       # must not raise on NaN
    dt = time.perf_counter() - t0
    assert json.loads(json.dumps(sig))
    assert np.isfinite(sig["slope_mean"]) and np.isfinite(sig["texture_mean"])
    assert 0 <= sig["dominant_class"] <= 7
    assert dt < 1.0, f"96x96 signature took {dt:.3f}s (expected < 1s)"

