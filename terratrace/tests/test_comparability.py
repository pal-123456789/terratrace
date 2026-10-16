"""Honest-regime comparability gate: tests built on the REAL defect.

The real matched-footprint run (artifacts/mf_real) asked for a 40 km common
window. The cached Earth tiles were smaller, so crop_center truncated them:
Craters of the Moon 24360 m, Andes 33180 m, Nevada 36090 m, against Mars
39818 m. That is a ~1.63x footprint mismatch, and the recommended analog had the
smallest window. Mars MOLA (463 m spacing, 1389 m effective resolution under the
3x heuristic) was also compared at 500 m and 1000 m supports. The runner printed
neither problem.

These tests rebuild that provenance through the REAL code path (crop_center +
cell_provenance on grids with the real tile shapes) and assert the gate names
both problems. They also check that the planning helpers produce an honest cell
from the same tiles. This is METHOD VALIDATION of a labelling gate, not a
scientific claim about Mars.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network.
"""
import copy
import json

import numpy as np

from terratrace import comparability as comp, matched_benchmark as mb, synthetic

# Real tile shapes + source spacings, copied from the real run's provenance.
_REAL = {
    "mars_daedalia": ((957, 974), 463.0),
    "earth_andean_volcano": ((1106, 1114), 30.0),
    "earth_craters_of_the_moon": ((1112, 812), 30.0),
    "earth_nevada_basin": ((1481, 1203), 30.0),
}
_EARTH = ["earth_andean_volcano", "earth_craters_of_the_moon", "earth_nevada_basin"]
_REQUESTED_M = 40000.0


def _real_grids():
    return {u: np.zeros(shape) for u, (shape, _s) in _REAL.items()}


def _real_spacings():
    return {u: s for u, (_shape, s) in _REAL.items()}


def _real_cell_provenance(extent_m, support_m):
    """Per-unit provenance for one cell, produced by the REAL crop + provenance code."""
    prov = {}
    for uid, (shape, spacing) in _REAL.items():
        _sub, info = mb.crop_center(np.zeros(shape), spacing, extent_m)
        prov[uid] = mb.cell_provenance(uid, info, support_m)
    return prov


def _assert_plain_json(obj):
    """Only builtin JSON types (catches numpy scalars that json.dumps lets through)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            assert type(k) is str, k
            _assert_plain_json(v)
    elif isinstance(obj, list):
        for v in obj:
            _assert_plain_json(v)
    else:
        assert obj is None or type(obj) in (str, int, float, bool), (obj, type(obj))


def test_real_defect_is_flagged_mismatched_and_below_effective_resolution():
    prov = _real_cell_provenance(_REQUESTED_M, 500.0)
    # The rebuilt provenance reproduces the real run's realised extents.
    assert {u: p["actual_extent_m"] for u, p in prov.items()} == {
        "mars_daedalia": 39818.0, "earth_andean_volcano": 33180.0,
        "earth_craters_of_the_moon": 24360.0, "earth_nevada_basin": 36090.0}
    a = comp.assess_cell(prov)
    assert a["footprint_matched"] is False
    assert abs(a["extent_ratio"] - 39818.0 / 24360.0) < 1e-12
    assert 1.634 < a["extent_ratio"] < 1.635
    assert a["min_extent_m"] == 24360.0 and a["max_extent_m"] == 39818.0
    assert a["truncated_units"] == _EARTH          # Mars 39818 m is rounding, not truncation
    assert a["upsampling_units"] == ["mars_daedalia"]
    assert a["low_power_units"] == []
    assert a["honest"] is False
    assert comp.regime_label(a) == "footprint-mismatched+below-effective-resolution"
    # One issue per problem: 3 truncations + 1 footprint mismatch + 1 upsampling.
    assert len(a["issues"]) == 5, a["issues"]
    for uid in _EARTH:
        assert any(i.startswith(uid + ": window truncated") for i in a["issues"]), uid
    assert any(i.startswith("mars_daedalia: support 500 m is below its effective "
                            "resolution 1389 m") for i in a["issues"]), a["issues"]
    mismatch = [i for i in a["issues"] if i.startswith("footprint mismatch")]
    assert len(mismatch) == 1
    assert "24360 m (earth_craters_of_the_moon)" in mismatch[0]
    assert "39818 m (mars_daedalia)" in mismatch[0] and "1.635" in mismatch[0]


def test_no_cell_of_the_real_support_sweep_was_honest():
    # The real run swept supports 500/1000/2000 m at the 40 km request. At 2000 m
    # Mars clears its 1389 m floor, but the truncated Earth windows remain.
    labels = {s: comp.regime_label(comp.assess_cell(_real_cell_provenance(_REQUESTED_M, s)))
              for s in (500.0, 1000.0, 2000.0)}
    assert labels == {500.0: "footprint-mismatched+below-effective-resolution",
                      1000.0: "footprint-mismatched+below-effective-resolution",
                      2000.0: "footprint-mismatched"}, labels


def test_truly_matched_cell_is_honest():
    prov = {}
    for uid, spacing in (("a", 30.0), ("b", 30.0), ("c", 10.0)):
        _sub, info = mb.crop_center(np.zeros((200, 200)), spacing, 1800.0)
        prov[uid] = mb.cell_provenance(uid, info, 90.0)   # 90 m == 3 x 30 m: inclusive floor
    a = comp.assess_cell(prov)
    assert a["footprint_matched"] is True and a["honest"] is True
    assert a["extent_ratio"] == 1.0 and a["min_extent_m"] == a["max_extent_m"] == 1800.0
    assert a["truncated_units"] == a["upsampling_units"] == a["low_power_units"] == []
    assert a["issues"] == []
    assert comp.regime_label(a) == "honest"


def test_planning_helpers_turn_the_real_tiles_into_an_honest_cell():
    plan = comp.common_matched_extent(_real_grids(), _real_spacings(), _REQUESTED_M)
    assert plan["extent_m"] == 24360.0
    assert plan["limiting_unit"] == "earth_craters_of_the_moon"
    assert plan["reduced"] is True and plan["requested_m"] == _REQUESTED_M
    assert plan["available_m"]["mars_daedalia"] == 443091.0   # = real grid_extent_m
    # Fixing the footprint alone is not enough: at 500 m Mars is still below 1389 m.
    half = comp.assess_cell(_real_cell_provenance(plan["extent_m"], 500.0))
    assert half["footprint_matched"] is True and half["honest"] is False
    assert half["upsampling_units"] == ["mars_daedalia"]
    assert comp.regime_label(half) == "below-effective-resolution"
    sups = comp.honest_supports([500.0, 1000.0, 2000.0], _real_spacings())
    assert sups == [2000.0]
    a = comp.assess_cell(_real_cell_provenance(plan["extent_m"], sups[0]))
    assert a["truncated_units"] == [] and a["footprint_matched"] and a["honest"]
    # Mars realises 53 px * 463 m = 24539 m vs 24360 m: a pixel-rounding gap within tol.
    assert a["max_extent_m"] == 24539.0 and a["extent_ratio"] <= 1.05
    assert comp.regime_label(a) == "honest"


def test_low_power_suffix():
    prov = {}
    for uid in ("a", "b"):
        _sub, info = mb.crop_center(np.zeros((100, 100)), 30.0, 3000.0)
        prov[uid] = mb.cell_provenance(uid, info, 600.0)  # 3000 // 600 = 5 cells per side
    a = comp.assess_cell(prov)
    assert a["low_power_units"] == ["a", "b"] and a["honest"] is True
    assert comp.regime_label(a) == "honest+low-power"
    assert sum("low statistical power" in i for i in a["issues"]) == 2
    assert comp.regime_label(comp.assess_cell(prov, min_cells=5)) == "honest"
    prov["b"]["truncated"] = True                         # the suffix stacks on other regimes
    assert comp.regime_label(comp.assess_cell(prov)) == "footprint-mismatched+low-power"


def test_regime_label_covers_every_branch():
    cases = {
        (True, (), ()): "honest",
        (False, (), ()): "footprint-mismatched",
        (True, ("m",), ()): "below-effective-resolution",
        (False, ("m",), ()): "footprint-mismatched+below-effective-resolution",
        (False, ("m",), ("e",)): "footprint-mismatched+below-effective-resolution+low-power",
        (True, ("m",), ("e",)): "below-effective-resolution+low-power",
    }
    for (fm, up, lp), want in cases.items():
        got = comp.regime_label({"footprint_matched": fm, "upsampling_units": list(up),
                                 "low_power_units": list(lp)})
        assert got == want, (fm, up, lp, got)


def test_common_matched_extent_picks_the_smallest_available_window():
    grids = {"a": np.zeros((100, 120)), "b": np.zeros((200, 80)), "c": np.zeros((60, 60))}
    sp = {"a": 30.0, "b": 30.0, "c": 100.0}               # available: 3000, 2400, 6000 m
    assert comp.common_matched_extent(grids, sp) == {
        "extent_m": 2400.0, "limiting_unit": "b",
        "available_m": {"a": 3000.0, "b": 2400.0, "c": 6000.0},
        "requested_m": None, "reduced": False}
    big = comp.common_matched_extent(grids, sp, 5000.0)
    assert big["extent_m"] == 2400.0 and big["limiting_unit"] == "b" and big["reduced"] is True
    small = comp.common_matched_extent(grids, sp, 1000.0)
    assert small["extent_m"] == 1000.0 and small["reduced"] is False
    assert small["requested_m"] == 1000.0 and small["limiting_unit"] == "b"
    shared = comp.common_matched_extent(grids, 30.0)      # scalar spacing
    assert shared["available_m"] == {"a": 3000.0, "b": 2400.0, "c": 1800.0}
    assert shared["limiting_unit"] == "c" and shared["extent_m"] == 1800.0
    # The returned extent is realised on every unit with no truncation.
    for uid, g in grids.items():
        _sub, info = mb.crop_center(g, sp[uid], big["extent_m"])
        assert not info["truncated"], uid
    assert comp.available_extent_m(np.zeros((7, 9)), 2.5) == 17.5


def test_support_floor_and_honest_supports():
    sp = {"mars": 463.0, "earth": 30.0}
    assert comp.support_floor_m(sp) == {"floor_m": 1389.0, "limiting_unit": "mars",
                                        "effective_m": {"earth": 90.0, "mars": 1389.0}}
    assert comp.honest_supports([500, 1000, 1500, 2000], sp) == [1500, 2000]
    assert comp.honest_supports([2000, 500, 1389, 1500], sp) == [1389.0, 1500.0, 2000.0]
    assert comp.support_floor_m(sp, res_factor=2.0)["floor_m"] == 926.0
    # Cross-check against the harness's own flag: a support is honest exactly when
    # no unit's cell_provenance raises upsampling_risk.
    honest = comp.honest_supports([500.0, 1000.0, 1389.0, 1500.0, 2000.0], _real_spacings())
    for s in (500.0, 1000.0, 1389.0, 1500.0, 2000.0):
        flagged = any(p["upsampling_risk"]
                      for p in _real_cell_provenance(24360.0, s).values())
        assert (s in honest) == (not flagged), s


def test_end_to_end_matched_cell_truncation_is_caught_then_fixed():
    grids = {
        "ref": synthetic.rough_field((160, 160), amplitude=25.0, seed=1),
        "A": synthetic.rough_field((160, 160), amplitude=4.0, seed=2),
        "B_small": synthetic.rough_field((100, 100), amplitude=25.0, seed=3),
    }
    dx, support = 30.0, 90.0
    naive = mb.matched_cell(grids, dx, "ref", 4200.0, support)   # B_small holds 3000 m
    a = comp.assess_cell(naive["provenance"])
    assert a["truncated_units"] == ["B_small"] and a["footprint_matched"] is False
    assert abs(a["extent_ratio"] - 4200.0 / 3000.0) < 1e-12
    assert comp.regime_label(a) == "footprint-mismatched"
    plan = comp.common_matched_extent(grids, dx, 4200.0)
    assert plan["extent_m"] == 3000.0 and plan["limiting_unit"] == "B_small"
    assert plan["reduced"] is True
    fixed = mb.matched_cell(grids, dx, "ref", plan["extent_m"], support)
    b = comp.assess_cell(fixed["provenance"])
    assert b["footprint_matched"] is True and b["truncated_units"] == []
    assert b["extent_ratio"] == 1.0
    assert comp.regime_label(b) == "honest"


def test_mismatched_control_is_flagged_by_ratio_alone():
    # The harness's own mismatched control truncates nothing, but its windows differ
    # by design. The extent-ratio check alone must catch that.
    grids = {"ref": synthetic.rough_field((160, 160), amplitude=25.0, seed=1),
             "A": synthetic.rough_field((160, 160), amplitude=4.0, seed=2)}
    cell = mb.mismatched_cell(grids, 30.0, "ref", 4200.0, 1500.0, 90.0)
    a = comp.assess_cell(cell["provenance"])
    assert a["truncated_units"] == [] and a["upsampling_units"] == []
    assert a["footprint_matched"] is False and a["extent_ratio"] == 2.8
    assert len(a["issues"]) == 1 and a["issues"][0].startswith("footprint mismatch")
    assert comp.regime_label(a) == "footprint-mismatched"


def test_outputs_json_serialisable_deterministic_and_input_untouched():
    prov = _real_cell_provenance(_REQUESTED_M, 500.0)
    snapshot = copy.deepcopy(prov)
    a = comp.assess_cell(prov)
    assert prov == snapshot                                # input not mutated
    reordered = {u: prov[u] for u in reversed(list(prov))}
    assert comp.assess_cell(reordered) == a == comp.assess_cell(prov)
    outs = [a, comp.regime_label(a),
            comp.common_matched_extent(_real_grids(), _real_spacings(), _REQUESTED_M),
            comp.support_floor_m(_real_spacings()),
            comp.honest_supports([500, 2000], _real_spacings())]
    for out in outs:
        _assert_plain_json(out)
        assert json.loads(json.dumps(out, allow_nan=False)) == out


def test_invalid_inputs_fail_loudly():
    for call, exc in ((lambda: comp.assess_cell({}), ValueError),
                      (lambda: comp.common_matched_extent({}, 30.0), ValueError),
                      (lambda: comp.common_matched_extent({"a": np.zeros((4, 4))}, -1.0),
                       ValueError),
                      (lambda: comp.common_matched_extent({"a": np.zeros((4, 4))}, {}),
                       KeyError),
                      (lambda: comp.support_floor_m(30.0), TypeError),
                      (lambda: comp.available_extent_m(np.zeros(5), 30.0), ValueError)):
        try:
            call()
        except exc:
            continue
        raise AssertionError(f"expected {exc.__name__}")


def test_default_study_hash_unchanged_by_this_module():
    # The gate only reads provenance; it must not perturb the gated default study.
    from terratrace import study
    h = study.run_study()["package_hash"]
    assert len(h) == 64 and all(ch in "0123456789abcdef" for ch in h)
    assert study.run_study()["package_hash"] == h
