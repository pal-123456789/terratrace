"""Co-registration fixtures: known-shift recovery and vertical-datum offset.

Mirrors the dependency-free style of test_features.py: plain ``def test_*``
functions, assert-based, no pytest. The sign convention under test is that the
shift returned by ``estimate_shift(ref, moving)``, when applied to ``moving``,
re-aligns it onto ``ref`` (minimises overlap RMSE).
"""
import numpy as np
from terratrace import coregister, synthetic


def _smooth_field(shape=(60, 60), seed=11):
    """Broad gaussian hill (strong gradient) plus mild seeded roughness.

    The hill supplies large-scale structure and the roughness decorrelates
    under any non-zero shift, so the overlap RMSE has a sharp, unique minimum
    at the true alignment -- ideal for exercising shift recovery.
    """
    hill = synthetic.gaussian_hill(shape, amplitude=12.0, sigma=10.0)
    rough = synthetic.rough_field(shape, amplitude=0.3, seed=seed)
    return hill + rough


def test_estimate_shift_recovers_known_translation():
    field = _smooth_field((60, 60), seed=11)
    dy0, dx0 = 2, -3
    c = 4.5  # constant vertical bias must not fool the horizontal search
    moving = coregister.apply_shift(field, dy0, dx0) + c

    est = coregister.estimate_shift(field, moving, max_shift=5)
    # The shift that re-aligns moving to ref is the opposite of the one used.
    assert est["dy"] == -dy0, est
    assert est["dx"] == -dx0, est
    assert est["max_shift"] == 5, est
    # Sub-pixel refinement stays within a pixel of the integer optimum.
    assert abs(est["dy_subpix"] - est["dy"]) <= 1.0, est
    assert abs(est["dx_subpix"] - est["dx"]) <= 1.0, est

    # Applying the recovered shift to moving minimises the overlap RMSE.
    realigned = coregister.apply_shift(moving, est["dy"], est["dx"])
    off_after = coregister.estimate_vertical_offset(field, realigned)
    rmse_after = coregister.overlap_rmse(field, realigned - off_after)
    off_before = coregister.estimate_vertical_offset(field, moving)
    rmse_before = coregister.overlap_rmse(field, moving - off_before)
    assert rmse_after < 1e-6, rmse_after
    assert rmse_after < 0.1 * rmse_before, (rmse_after, rmse_before)


def test_estimate_vertical_offset_recovers_constant():
    field = _smooth_field((50, 50), seed=3)
    c = 7.25
    got = coregister.estimate_vertical_offset(field, field + c)
    assert abs(got - c) < 1e-9, got
    # Offset is signed: moving minus ref.
    assert coregister.estimate_vertical_offset(field, field - 2.0) < 0.0


def test_identical_arrays_zero_shift_zero_offset():
    field = _smooth_field((40, 40), seed=5)
    est = coregister.estimate_shift(field, field, max_shift=4)
    assert est["dy"] == 0 and est["dx"] == 0, est
    assert est["rmse"] < 1e-9, est["rmse"]
    assert abs(coregister.estimate_vertical_offset(field, field)) < 1e-12


def test_coregister_aligns_and_returns_keys():
    field = _smooth_field((60, 60), seed=9)
    dy0, dx0 = -2, 3
    c = -5.0
    moving = coregister.apply_shift(field, dy0, dx0) + c

    out = coregister.coregister(field, moving, max_shift=5)
    for k in ("dy", "dx", "dy_subpix", "dx_subpix", "rmse",
              "vertical_offset", "aligned"):
        assert k in out, k

    assert out["dy"] == -dy0 and out["dx"] == -dx0, out
    assert abs(out["vertical_offset"] - c) < 1e-6, out["vertical_offset"]

    rmse_aligned = coregister.overlap_rmse(field, out["aligned"])
    rmse_unaligned = coregister.overlap_rmse(field, moving)
    assert np.isfinite(rmse_aligned), rmse_aligned
    assert rmse_aligned < 0.1 * rmse_unaligned, (rmse_aligned, rmse_unaligned)


def test_nan_patch_does_not_break_recovery():
    field = _smooth_field((60, 60), seed=13)
    dy0, dx0 = 2, -3
    moving = coregister.apply_shift(field, dy0, dx0)
    moving = moving.copy()
    moving[10:20, 15:25] = np.nan  # nodata hole must not crash or mislead

    est = coregister.estimate_shift(field, moving, max_shift=5)
    assert est["dy"] == -dy0 and est["dx"] == -dx0, est

    out = coregister.coregister(field, moving, max_shift=5)
    rmse_aligned = coregister.overlap_rmse(field, out["aligned"])
    rmse_unaligned = coregister.overlap_rmse(field, moving)
    assert np.isfinite(rmse_aligned), rmse_aligned
    assert rmse_aligned < 0.1 * rmse_unaligned, (rmse_aligned, rmse_unaligned)


def test_apply_shift_fills_edges_with_nan_no_wrap():
    field = synthetic.gaussian_hill((20, 20), amplitude=5.0, sigma=4.0)
    down_right = coregister.apply_shift(field, 2, 3)
    assert np.all(np.isnan(down_right[:2, :])), "top rows should be NaN"
    assert np.all(np.isnan(down_right[:, :3])), "left cols should be NaN"
    # Interior content is preserved (translated), not wrapped.
    assert np.allclose(down_right[2:, 3:], field[:-2, :-3], equal_nan=True)


def test_overlap_rmse_nan_when_no_overlap():
    a = np.array([[1.0, np.nan], [np.nan, 2.0]])
    b = np.array([[np.nan, 3.0], [4.0, np.nan]])
    assert np.isnan(coregister.overlap_rmse(a, b))
    assert coregister.overlap_rmse(a, a) == 0.0
