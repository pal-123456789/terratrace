"""Tests for the depression-filled D8 flow-accumulation dissection descriptor.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network --
small synthetic surfaces with analytic answers, mirroring the style of
test_kh_roughness.py / test_descriptors.py. The six correctness oracles here pin
the algorithm: flow conservation, depression removal, downhill routing on a
tilted plane, valley convergence, roughness discrimination, and NaN-safety.

These exercise a purely GEOMETRIC flow-routing descriptor; nothing here is a
claim of water, fluvial, climate, or mission processes on any body.
"""
import json

import numpy as np

from terratrace import drainage, synthetic

_SIG_KEYS = {"channel_fraction", "mean_log_acc", "max_acc_fraction",
             "drainage_density_proxy"}


def _tilt_down_rows(shape, dx=1.0):
    """z[i, j] = -i*dx: a plane that slopes strictly downhill with row index."""
    ii = np.indices(shape)[0]
    return -ii.astype(float) * dx


def _v_valley(shape):
    """z[i, j] = |j - C//2|: a V-shaped valley whose axis is the centre column."""
    jj = np.indices(shape)[1]
    return np.abs(jj - shape[1] // 2).astype(float)


def _outlet_sum(acc, flowdir, finite):
    """Total accumulation held by the outlet cells (flowdir == -1, finite)."""
    outlet = (flowdir == -1) & finite
    return float(np.nansum(acc[outlet]))


def test_api_shapes_and_dtypes():
    z = synthetic.plane((30, 30), slope_x=0.02, dx=5.0) + synthetic.rough_field(
        (30, 30), amplitude=1.0, seed=1)
    filled = drainage.fill_depressions(z)
    flowdir = drainage.d8_flow_direction(z)
    acc = drainage.flow_accumulation(z)
    assert filled.shape == flowdir.shape == acc.shape == z.shape
    assert filled.dtype == np.float64
    assert flowdir.dtype == np.int8
    assert acc.dtype == np.float64
    # fill_and_flowdirs returns the same two arrays as the thin wrappers
    f2, d2 = drainage.fill_and_flowdirs(z)
    assert np.array_equal(f2, filled)
    assert np.array_equal(d2, flowdir)
    # flow directions are exactly {-1} u {0..7}; outlets/NaN are -1
    vals = set(np.unique(flowdir).tolist())
    assert vals <= set(range(-1, 8)), vals


def test_flow_conservation_invariants():
    # Oracle 1: on any finite grid every finite cell has acc >= 1, max(acc) <=
    # n_finite, and the accumulations of the OUTLET cells sum to exactly
    # n_finite (every cell drains to some domain-edge outlet).
    z = synthetic.plane((80, 80), slope_x=0.02, dx=10.0) + synthetic.rough_field(
        (80, 80), amplitude=2.0, seed=7)
    acc = drainage.flow_accumulation(z)
    flowdir = drainage.d8_flow_direction(z)
    finite = np.isfinite(z)
    n = int(finite.sum())
    assert np.all(acc[finite] >= 1.0)
    assert float(np.nanmax(acc)) <= n
    assert abs(_outlet_sum(acc, flowdir, finite) - n) < 1e-6


def test_fill_ge_original_and_single_pit_removed():
    # Oracle 2: filled >= z everywhere finite, and a lone deep interior pit is
    # raised to its spill level (strictly above its original depth).
    plane = synthetic.plane((21, 21), slope_x=0.01, dx=1.0)
    z = plane.copy()
    ci, cj = 10, 10
    z[ci, cj] -= 50.0                       # a deep central pit
    filled = drainage.fill_depressions(z)
    finite = np.isfinite(z)
    assert np.all(filled[finite] >= z[finite] - 1e-12)
    assert filled[ci, cj] > z[ci, cj]       # pit filled up to the spill level
    # the pit is no longer the strict minimum of its 3x3 neighbourhood
    nbhd = filled[ci - 1:ci + 2, cj - 1:cj + 2]
    assert filled[ci, cj] >= float(np.min(nbhd)) - 1e-12


def test_tilted_plane_runs_downhill():
    # Oracle 3: on a plane sloping down with row index, flow runs down-slope. The
    # top (highest) row is a pure source band (acc == 1 everywhere), the deepest
    # accumulation equals a full column of upslope cells (max(acc) == R-1), and
    # flow conservation holds.
    R = C = 80
    z = _tilt_down_rows((R, C), dx=1.0)
    acc = drainage.flow_accumulation(z)
    flowdir = drainage.d8_flow_direction(z)
    finite = np.isfinite(z)
    assert np.all(acc[0, :] == 1.0)                 # highest row: nothing upstream
    assert int(np.nanmax(acc)) == R - 1             # a whole down-slope column
    assert abs(_outlet_sum(acc, flowdir, finite) - int(finite.sum())) < 1e-6


def test_v_valley_axis_concentrates_flow():
    # Oracle 4: a V-shaped valley routes its flanks onto the valley axis, so the
    # axis column carries strictly more mean accumulation than the flank columns.
    R = C = 40
    z = _v_valley((R, C))
    acc = drainage.flow_accumulation(z)
    axis = float(np.nanmean(acc[:, C // 2]))
    flank = float(np.nanmean(acc[:, [3, 6, C - 4, C - 7]]))
    assert axis > flank, (axis, flank)


def test_dissection_discriminates_roughness():
    # Oracle 5: roughness reorganises drainage. A smooth tilted plane routes flow
    # into many parallel, organised columns (high mean_log_acc, low peak
    # concentration); a seeded rough surface fragments that organisation and
    # concentrates flow at filled-depression spill points. So a dissected surface
    # has a strictly HIGHER peak flow concentration (max_acc_fraction) and a
    # strictly LOWER organised accumulation (mean_log_acc) than the smooth plane.
    # (channel_fraction thresholds accumulation at its own quantile and is close
    # to 1 - channel_quantile by construction, so it is NOT the discriminator.)
    smooth = synthetic.plane((80, 80), slope_x=0.05, dx=1.0)
    rough = smooth + synthetic.rough_field((80, 80), amplitude=3.0, seed=5)
    s = drainage.drainage_signature(smooth)
    r = drainage.drainage_signature(rough)
    assert r["max_acc_fraction"] > s["max_acc_fraction"], (r, s)
    assert r["mean_log_acc"] < s["mean_log_acc"], (r, s)
    # the self-normalising channel fraction sits near 1 - channel_quantile
    assert abs(s["channel_fraction"] - 0.05) < 0.03, s["channel_fraction"]


def test_nan_safe():
    # Oracle 6: a few NaN cells raise nothing, carry NaN accumulation, leave the
    # rest finite, and conservation still holds over the finite cells.
    z = synthetic.plane((50, 50), slope_x=0.04, dx=8.0) + synthetic.rough_field(
        (50, 50), amplitude=1.0, seed=5)
    z[10, 10] = np.nan
    z[25, 30] = np.nan
    z[40, 5] = np.nan
    acc = drainage.flow_accumulation(z)
    flowdir = drainage.d8_flow_direction(z)
    finite = np.isfinite(z)
    assert np.isnan(acc[10, 10]) and np.isnan(acc[25, 30]) and np.isnan(acc[40, 5])
    assert np.all(np.isfinite(acc[finite]))
    assert flowdir[10, 10] == -1                       # NaN cells never route
    assert abs(_outlet_sum(acc, flowdir, finite) - int(finite.sum())) < 1e-6
    sig = drainage.drainage_signature(z)
    assert np.isfinite(sig["mean_log_acc"])
    assert json.loads(json.dumps(sig))


def test_signature_keys_types_json_and_determinism():
    z = (synthetic.plane((48, 48), slope_x=0.03, slope_y=0.01, dx=5.0)
         + synthetic.rough_field((48, 48), amplitude=1.0, seed=3))
    sig = drainage.drainage_signature(z, dx=5.0)
    assert set(sig) == _SIG_KEYS, set(sig)
    assert all(type(v) is float for v in sig.values()), sig
    assert all(np.isfinite(v) for v in sig.values()), sig
    assert 0.0 < sig["max_acc_fraction"] <= 1.0, sig["max_acc_fraction"]
    assert 0.0 <= sig["channel_fraction"] <= 1.0, sig["channel_fraction"]
    # drainage_density_proxy == channel_fraction / dx
    assert abs(sig["drainage_density_proxy"] - sig["channel_fraction"] / 5.0) < 1e-12
    dumped = json.dumps(sig)
    assert isinstance(dumped, str) and json.loads(dumped)
    assert drainage.drainage_signature(z, dx=5.0) == sig       # deterministic


def test_all_nan_signature_is_nan():
    sig = drainage.drainage_signature(np.full((8, 8), np.nan))
    assert set(sig) == _SIG_KEYS, set(sig)
    assert all(type(v) is float and np.isnan(v) for v in sig.values()), sig
    # an all-NaN grid also routes nothing and accumulates NaN everywhere
    acc = drainage.flow_accumulation(np.full((8, 8), np.nan))
    assert np.all(np.isnan(acc))




