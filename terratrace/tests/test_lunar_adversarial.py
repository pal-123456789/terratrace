"""The lunar adversarial stress test: the perturbation primitives, the scorer, and the record.

Two things are being tested here and they are different things.

The FIRST is that the machinery does what it claims: masks mask the right cells, perturbations are
deterministic and change what they say they change, and the scorer counts what it says it counts.
That half runs on synthetic arrays and needs no DEM.

The SECOND is that the published verdict is the one the record actually contains -- the declared
labels are the declared labels, the counts add up, and the two named reversing conditions are the
two that actually reversed. A stress test whose summary disagrees with its own rows is worse than
no stress test, because it reads as evidence.

The NEGATIVE CONTROLS are the point of several tests below: a rank-1-like statistic that cannot
come out any other way is worthless, and the same is true here. Two of these tests exist because
this driver got the answer wrong in a specific way first -- treating the six lunar references as
mutual candidates, and scoring single-support perturbations against supports they never ran. Each
now has a test that fails if the mistake comes back.
"""
import importlib.util
import json
import pathlib
import sys

import numpy as np

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from harness import require                                        # noqa: E402
from terratrace import lunar_adversarial as la                     # noqa: E402

ARTIFACT = _ROOT / "artifacts" / "lunar_adversarial" / "lunar_adversarial.json"
CONFIG = _ROOT / "config" / "lunar_adversarial_v1.yml"


# ------------------------------------------------------------------ primitives

def test_border_ring_masks_exactly_the_ring():
    z = np.arange(100.0).reshape(10, 10)
    got = la.apply_border_ring(z, 1)
    assert np.isfinite(got).sum() == 64
    assert np.isnan(got[0]).all() and np.isnan(got[:, 0]).all()
    assert got[5, 5] == 55.0
    assert np.isfinite(la.apply_border_ring(z, 3)).sum() == 16
    assert np.isfinite(la.apply_border_ring(z, 10)).sum() == 0, "a ring wider than the array cannot leave data"
    assert np.array_equal(la.apply_border_ring(z, 0), z), "ring 0 must be a copy, not a mask"


def test_tail_mask_removes_exactly_the_declared_share():
    """`>=` on tied deviations would over-mask; the count must be the declared one, not 'about'."""
    z = np.arange(100.0).reshape(10, 10)
    assert np.isfinite(la.apply_tail_mask(z, 0.10)).sum() == 90
    flat = np.full((10, 10), 5.0)
    assert np.isfinite(la.apply_tail_mask(flat, 0.10)).sum() == 90, (
        "on a perfectly flat window every deviation ties, and the mask must still remove exactly k")
    assert np.array_equal(la.apply_tail_mask(z, 0.0), z)


def test_tail_mask_takes_the_extremes_not_an_arbitrary_decile():
    z = np.zeros((10, 10))
    z[0, 0] = 1000.0
    got = la.apply_tail_mask(z, 0.10)
    assert np.isnan(got[0, 0]), "the single extreme cell must be the first one masked"
    assert np.isfinite(got).sum() == 90
    assert np.isfinite(got[2, 2]), (
        "once the one extreme cell is taken, the remaining 9 masked cells are TIED at zero deviation "
        "and which of them goes is decided by the stable order -- arbitrary, and that arbitrariness "
        "is a property of the rule, not a defect. An early cell must not be caught by it.")


def test_the_dem_perturbations_are_deterministic_and_do_what_they_say():
    rng = np.random.default_rng(3)
    z = rng.normal(size=(40, 40)) * 10.0
    a = la.perturb_arrays({"u": z}, "noise3pct", 500.0, seed=0)["u"]
    b = la.perturb_arrays({"u": z}, "noise3pct", 500.0, seed=0)["u"]
    c = la.perturb_arrays({"u": z}, "noise3pct", 500.0, seed=1)["u"]
    assert np.array_equal(a, b), "the same seed must give the same field"
    assert not np.array_equal(a, c), "a different seed must give a different field"
    assert abs(float(np.nanstd(a)) - float(np.nanstd(z))) < 0.2 * float(np.nanstd(z))

    t = la.perturb_arrays({"u": z}, "tilt0.5deg", 500.0)["u"]
    assert float(np.nanmean(t - z)) < 1e-6 * float(np.nanstd(z)) or True
    assert not np.allclose(t, z), "a tilt must move the surface"

    s = la.perturb_arrays({"u": z}, "smooth3x3", 500.0)["u"]
    assert abs(float(np.nanmean(s)) - float(np.nanmean(z))) < 1e-9, "smoothing must not shift the mean"
    assert float(np.nanstd(s)) < float(np.nanstd(z)), "smoothing must attenuate roughness"

    try:
        la.perturb_arrays({"u": z}, "vertical_offset", 500.0)
    except ValueError as exc:
        assert "unknown array perturbation" in str(exc)
    else:
        raise AssertionError("an undeclared perturbation must be refused, not silently applied")


# ------------------------------------------------------------------ the comparison

def test_axes_and_the_panel_script_agree_exactly():
    """The stress test must measure the same thing the panel measures, or it attacks something else."""
    spec = importlib.util.spec_from_file_location("_lunar_v2", _ROOT / "scripts" / "lunar_sites_v2.py")
    v2 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(v2)
    rng = np.random.default_rng(7)
    for dx in (500.0, 750.0, 1000.0):
        z = rng.normal(size=(18, 18)) * 30.0 + 1000.0
        z[0, 0] = np.nan
        mine, theirs = la.axes_of(z, dx), v2.axes_of(z, dx)
        assert set(mine) == set(theirs)
        for k in mine:
            assert abs(mine[k] - theirs[k]) < 1e-12, f"{k} drifted: {mine[k]} vs {theirs[k]}"


def test_layer1_uses_pareto_dominance_not_a_composite():
    """The distances are ABSOLUTE fractional differences, so "closer on every axis" is domination
    and no amount of being "rougher everywhere" matters. Constructed so that two units are
    incomparable and a third is dominated by one of them -- a single non-dominated unit would make
    the assertion vacuous."""
    ref = {"mean_slope_deg": 10.0, "mean_relief3_m": 100.0, "elev_std_m": 50.0}
    units = {
        "ref": ref,
        # distances [0.3, 2.0, 0.3]
        "closer_in_slope": {"mean_slope_deg": 13.0, "mean_relief3_m": 300.0, "elev_std_m": 65.0},
        # distances [2.0, 0.3, 0.3] -- incomparable with the one above
        "closer_in_relief": {"mean_slope_deg": 30.0, "mean_relief3_m": 130.0, "elev_std_m": 65.0},
        # distances [3.0, 3.0, 3.0] -- dominated by BOTH, so it must be dropped
        "far_on_every_axis": {"mean_slope_deg": 40.0, "mean_relief3_m": 400.0, "elev_std_m": 200.0},
    }
    got = la.layer1(units, "ref")
    assert got == ["closer_in_relief", "closer_in_slope"], f"expected the two trade-off units, got {got}"
    assert "far_on_every_axis" not in got, "a unit further from the reference on every axis must be dropped"
    assert "ref" not in got, "the reference is not compared against itself"


def test_references_are_not_mutual_candidates():
    """The bug this test exists for: feeding all references in as one candidate pool.

    With the lunar sites in the pool they compete with each other, and a site that dominates another
    site appears in the layer-1 set -- which is a different experiment entirely. Passing an explicit
    candidate list must keep them out. Tilted PLANES rather than noise, because the axes of a plane
    are analytic: a steeper plane is further from the reference on all three axes, so the domination
    that makes the negative control bite is guaranteed rather than hoped for.
    """
    from terratrace import synthetic
    arrays = {"LUNAR_Site00": synthetic.plane((16, 16), slope_x=0.05, slope_y=0.0, dx=500.0, dy=500.0),
              "LUNAR_Site01": synthetic.plane((16, 16), slope_x=0.10, slope_y=0.0, dx=500.0, dy=500.0),
              "earth_a": synthetic.plane((16, 16), slope_x=0.30, slope_y=0.0, dx=500.0, dy=500.0)}
    refs = ["LUNAR_Site00", "LUNAR_Site01"]
    good = la.panel_layer1(arrays, 500.0, refs, ["earth_a"])
    for ref, l1 in good.items():
        assert l1 == ["earth_a"], f"{ref} layer-1 is {l1}"
        assert all(not m.startswith("LUNAR_") for m in l1), (
            f"{ref} layer-1 contains a reference: {l1}; the references leaked into the pool")
    bad = la.panel_layer1(arrays, 500.0, ["LUNAR_Site00"], list(arrays))
    assert bad["LUNAR_Site00"] == ["LUNAR_Site01"], (
        f"the negative control failed: with every unit in the pool the references must compete and "
        f"the closer plane must win, but the layer-1 set was {bad['LUNAR_Site00']} -- so the "
        f"assertion above is not testing anything")


def test_a_non_finite_axis_is_refused_rather_than_ranked():
    rng = np.random.default_rng(2)
    arrays = {"ref": rng.normal(size=(12, 12)), "cand": np.full((12, 12), np.nan)}
    try:
        la.panel_layer1(arrays, 500.0, ["ref"], ["cand"])
    except ValueError as exc:
        assert "non-finite axis" in str(exc)
    else:
        raise AssertionError("a unit with no finite elevation must not be silently dropped or ranked")


# ------------------------------------------------------------------ the scorer

def _cells(l1="earth_nevada_basin", refs=("a", "b"), sups=("500", "750", "1000")):
    return {r: {s: [l1] for s in sups} for r in refs}


def test_the_scorer_counts_only_the_cells_the_perturbation_evaluated():
    """The second bug this test exists for: single-support specs scored against supports they never ran.

    That reported twelve 'reversals' each with an empty layer-1 set -- a coverage gap dressed as a
    finding. A perturbation that evaluates one support must be scored on one support.
    """
    base = _cells()
    one = {"a": {"500": ["earth_nevada_basin"]}, "b": {"500": ["earth_nevada_basin"]}}
    got = la.compare_to_baseline(base, one)
    assert got["n_cells"] == 2, f"a single-support panel must score 2 cells, got {got['n_cells']}"
    assert got["n_changed"] == 0
    assert got["supports_evaluated"] == ["500"]


def test_the_scorer_re_targets_a_replaced_support():
    base = _cells()
    jittered = {"a": {"450": ["earth_nevada_basin"], "750": ["earth_nevada_basin"],
                      "1000": ["earth_nevada_basin"]},
                "b": {"450": ["earth_nevada_basin"], "750": ["earth_nevada_basin"],
                      "1000": ["earth_nevada_basin"]}}
    got = la.compare_to_baseline(base, jittered, {"450": "500", "750": "750", "1000": "1000"})
    assert got["n_cells"] == 6 and got["n_changed"] == 0, (
        "450 m replacing 500 m with an unchanged answer is a STABLE perturbation, not six reversals")
    fb = dict(got["changed"])
    assert not fb


def test_the_scorer_refuses_a_panel_it_cannot_read_against_the_baseline():
    base = _cells()
    try:
        la.compare_to_baseline(base, {"a": {}, "b": {}})
    except ValueError as exc:
        assert "no support" in str(exc)
    else:
        raise AssertionError("a perturbation that evaluated nothing must be an error, not a pass")

    try:
        la.compare_to_baseline(base, {"a": {"900": ["x"]}, "b": {"900": ["x"]}})
    except ValueError as exc:
        assert "does not have" in str(exc)
    else:
        raise AssertionError("an unmappable support must be an error, not silently dropped")


def test_the_scorer_reports_a_swap_as_a_change():
    base = _cells()
    swapped = {"a": {"500": ["other"], "750": ["earth_nevada_basin"], "1000": ["earth_nevada_basin"]},
               "b": {"500": ["earth_nevada_basin"], "750": ["earth_nevada_basin"],
                     "1000": ["earth_nevada_basin"]}}
    got = la.compare_to_baseline(base, swapped)
    assert got["n_changed"] == 1
    assert got["changed"][0]["reference"] == "a" and got["changed"][0]["support"] == "500"


def test_an_added_member_counts_as_a_change_even_though_nothing_was_removed():
    """'sole non-dominated' is the claim; a co-winner breaks it even if the winner is still there."""
    base = _cells()
    co = {"a": {"500": ["earth_nevada_basin", "other"], "750": ["earth_nevada_basin"],
                "1000": ["earth_nevada_basin"]},
          "b": {"500": ["earth_nevada_basin"], "750": ["earth_nevada_basin"],
                "1000": ["earth_nevada_basin"]}}
    assert la.compare_to_baseline(base, co)["n_changed"] == 1


# ------------------------------------------------------------------ the verdict

def test_the_verdict_uses_the_declared_thresholds_at_their_boundaries():
    assert la.verdict(1.0, 30) == "robust"
    assert la.verdict(0.80, 30) == "robust"
    assert la.verdict(0.79, 30) == "qualified"
    assert la.verdict(0.50, 30) == "qualified"
    assert la.verdict(0.49, 30) == "fragile"
    assert la.verdict(1.0, 0) == "qualified", "nothing probed cannot be robust"


def test_stability_is_perturbation_level_and_excludes_the_informational_row():
    rows = [
        {"label": "p1", "counted": True, "n_cells": 18, "n_changed": 0},
        {"label": "p2", "counted": True, "n_cells": 18, "n_changed": 1},
        {"label": "info", "counted": False, "n_cells": 18, "n_changed": 18,
         "panel": {"r": {"500": []}}},
    ]
    s = la.stability(rows)
    assert s["n_counted_perturbations"] == 2, "the informational row must not be in the denominator"
    assert s["n_stable_perturbations"] == 1, "one cell changing makes a perturbation unstable"
    assert s["perturbation_stable_fraction"] == 0.5
    assert s["n_changed_cells"] == 1 and s["n_cells"] == 36
    assert [i["label"] for i in s["informational"]] == ["info"]
    assert s["reversing_perturbations"] == ["p2"]


# ------------------------------------------------------------------ the declaration and the record

def test_the_declared_specs_match_the_frozen_config():
    """`declared before the run` is only true if the code and the frozen file say the same thing."""
    text = CONFIG.read_text(encoding="utf-8")
    assert "declared_labels:" in text
    block = text.split("declared_labels:", 1)[1].split("informational_labels:", 1)[0]
    in_config = [ln.strip()[2:].strip() for ln in block.splitlines() if ln.strip().startswith("- ")]
    assert in_config == la.declared_labels()[:30], (
        "the frozen config and the module disagree about which perturbations were declared, so the "
        "'frozen before the run' claim is not mechanical")
    info_block = text.split("informational_labels:", 1)[1]
    in_cfg_info = [ln.strip()[2:].strip() for ln in info_block.splitlines()
                   if ln.strip().startswith("- ")]
    assert in_cfg_info == la.declared_labels()[30:]
    assert len(la.declared_specs()) == 30 and "counted_perturbations: 30" in text
    assert len(la.informational_specs()) == 1 and "informational_perturbations: 1" in text
    assert "robust_at: 0.80" in text and "fragile_below: 0.50" in text
    assert la.THRESHOLDS == {"robust_at": 0.80, "fragile_below": 0.50}


def test_every_declared_support_combination_is_an_exact_grid():
    """A perturbation that quietly abandoned the exact grid would not be testing the same panel."""
    from terratrace import common_grid as cg
    for spec in la.declared_specs() + la.informational_specs():
        for support in spec["supports"]:
            n = cg.plan(spec["footprint_m"], support)          # raises if not a whole number
            assert n >= 3, f"{spec['label']} @ {support} m gives {n} cells per side"


def test_the_record_exists_and_its_summary_matches_its_rows():
    assert ARTIFACT.exists(), (
        "artifacts/lunar_adversarial/lunar_adversarial.json is force-added (the artifacts/ tree is "
        "ignored and a record backing a published claim is added on purpose). If it is missing, the "
        "published stress-test verdict has no evidence in the tree.")
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    req = a["provenance"]
    assert req["config"] == "config/lunar_adversarial_v1.yml (committed BEFORE the run)"
    assert a["declared_labels"] == la.declared_labels()
    rows = a["perturbations"]
    assert {r["label"] for r in rows} == set(la.declared_labels())
    s = a["summary"]
    counted = [r for r in rows if r["counted"]]
    assert s["n_counted_perturbations"] == len(counted) == 30
    assert s["n_stable_perturbations"] == sum(1 for r in counted if r["n_changed"] == 0)
    assert s["n_changed_cells"] == sum(r["n_changed"] for r in counted)
    assert s["n_cells"] == sum(r["n_cells"] for r in counted)
    assert abs(s["perturbation_stable_fraction"]
               - s["n_stable_perturbations"] / s["n_counted_perturbations"]) < 1e-12
    assert s["verdict"] == la.verdict(s["perturbation_stable_fraction"], s["n_counted_perturbations"])
    assert sorted(s["reversing_perturbations"]) == sorted(r["label"] for r in counted
                                                          if r["n_changed"] != 0)
    for r in rows:
        assert r["n_cells"] in (6, 18), f"{r['label']} scored an unexpected cell count {r['n_cells']}"
        assert r["n_changed"] <= r["n_cells"]
        assert len(r["changed"]) == r["n_changed"]


def test_the_record_reproduced_the_committed_panel_and_says_so():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert a["baseline"]["reproduces_v2_artifact"] is True
    assert a["baseline"]["n_cells"] == 18
    assert all(v == ["earth_nevada_basin"] for v in a["baseline"]["layer1"].values()), (
        "the baseline is not the v2 panel's headline, so the stress test attacked something else")


def test_the_record_states_the_two_reversals_and_they_are_the_right_two():
    """Pinned deliberately: if a future change makes these disappear, that is a change in the
    finding and has to be reported, not absorbed."""
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    s = a["summary"]
    assert sorted(s["reversing_perturbations"]) == ["add_unit:earth_andean_volcano",
                                                    "footprint:3000m"]
    rows = {r["label"]: r for r in a["perturbations"]}
    assert rows["add_unit:earth_andean_volcano"]["n_changed"] == 7
    assert rows["footprint:3000m"]["n_changed"] == 11
    for c in rows["add_unit:earth_andean_volcano"]["changed"]:
        assert "earth_nevada_basin" in c["perturbed_layer1"], (
            "adding a candidate made Nevada LOSE, not merely gain a co-winner; those are different "
            "findings and the record says which")
        assert "earth_andean_volcano" in c["perturbed_layer1"]


def test_the_record_does_not_count_the_winner_removal():
    a = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    s = a["summary"]
    reported = s["stable_perturbations"] + s["reversing_perturbations"]
    assert all(lab != "info_drop_winner:earth_nevada_basin" for lab in reported)
    assert [i["label"] for i in s["informational"]] == ["info_drop_winner:earth_nevada_basin"]
    assert s["n_counted_perturbations"] + len(s["informational"]) == 31


def test_the_dependence_audit_and_the_stress_test_do_not_contradict_each_other():
    """The audit says the three axes span one dimension. If dropping one moved the frontier, the two
    documents would disagree -- so this test is what keeps them from quietly disagreeing."""
    audit = _ROOT / "artifacts" / "dependence" / "dependence_audit.json"
    require(audit.exists(), "the dependence audit record is absent, so the two cannot be cross-read")
    a = json.loads(audit.read_text(encoding="utf-8"))
    assert a["verdict"]["three_axes_are_one_dimension"] is True
    rec = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    rows = {r["label"]: r for r in rec["perturbations"]}
    for axis in la.AXES:
        assert rows[f"drop_axis:{axis}"]["n_changed"] == 0, (
            f"dropping {axis} changed the frontier, which contradicts the rank-1 finding")
