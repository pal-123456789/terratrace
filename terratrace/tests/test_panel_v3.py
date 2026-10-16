"""Protocol v3 reference panel (terratrace.panel_v3), exercised WITHOUT rasterio or network.

Three layers, all offline and synthetic:

  * the resolution-change classifier, one test per class (incl. the exact v2
    situation, INDETERMINATE with layer 1 {X} -> RECOMMEND X = "stabilised");
  * the S / V / R rules on FABRICATED cells whose Pareto layer 1 and dominance matrix
    come from ``frontier.summarize`` on made-up distance vectors (so they are mutually
    consistent by construction), one boundary at a time;
  * two GROUND-TRUTH scenes driven through ``run_panel_v3_from_grids`` on the real
    engine: a SMOOTHNESS world (S supported, V not) and a SPECIFIC world (V supported,
    S not).

The rasterio seam ``matched_real.load_panel_grids`` is only ever monkeypatched here,
never called: it remains untested in this sandbox and is exercised by the real run.
"""
import contextlib
import copy
import hashlib
import importlib.util
import io
import json
import os
import shutil
import tempfile

from terratrace import confirmation as cf
from terratrace import frontier, matched_real, panel_v3, resolution, study, synthetic

RECOMMEND = cf.RECOMMEND
_S = {"name": "S", "type": "class_in_layer1", "class": "smooth_control"}
_V = {"name": "V", "type": "class_dominates", "winner_class": "basaltic",
      "loser_class": "smooth_control"}


# --------------------------------------------------------------------------- #
# classify_resolution_change -- one test per class                             #
# --------------------------------------------------------------------------- #
def _c(state, layer1, rec=None):
    return {"support_m": 240.0, "result_state": state, "pareto_layer1": list(layer1),
            "recommended_unit": rec}


def test_classify_unchanged():
    f = panel_v3.classify_resolution_change
    assert f(_c(RECOMMEND, ["X"], "X"), _c(RECOMMEND, ["X"], "X")) == "unchanged"
    assert f(_c("INDETERMINATE", ["X"]), _c("INDETERMINATE", ["X"])) == "unchanged"
    assert f(_c("TIE", ["X", "Y"]), _c("TIE", ["Y", "X"])) == "unchanged"   # a set


def test_classify_stabilised_is_the_v2_situation():
    """v2: every honest cell INDETERMINATE with the sole layer-1 unit X became a stable
    RECOMMEND of X under resolution matching. That is a stabilisation, not a reversal."""
    f = panel_v3.classify_resolution_change
    assert f(_c("INDETERMINATE", ["X"]), _c(RECOMMEND, ["X"], "X")) == "stabilised"
    assert f(_c("TIE", ["X"]), _c(RECOMMEND, ["X"], "X")) == "stabilised"
    # ... but RECOMMEND of a DIFFERENT unit is a reversal.
    assert f(_c("INDETERMINATE", ["X"]), _c(RECOMMEND, ["Y"], "Y")) == "reversed"


def test_classify_destabilised():
    f = panel_v3.classify_resolution_change
    assert f(_c(RECOMMEND, ["X"], "X"), _c("INDETERMINATE", ["X"])) == "destabilised"
    assert f(_c(RECOMMEND, ["X"], "X"), _c("TIE", ["X", "Y"])) == "destabilised"


def test_classify_reversed_all_four_patterns():
    f = panel_v3.classify_resolution_change
    # raw RECOMMEND X, matched RECOMMEND Y != X
    assert f(_c(RECOMMEND, ["X"], "X"), _c(RECOMMEND, ["Y"], "Y")) == "reversed"
    # raw RECOMMEND X, X not in the matched layer 1
    assert f(_c(RECOMMEND, ["X"], "X"), _c("TIE", ["Y", "Z"])) == "reversed"
    # raw layer 1 == {X}, X not in the matched layer 1 (here: the matched cell lost it)
    assert f(_c("INDETERMINATE", ["X"]), _c("TIE", ["Y", "Z"])) == "reversed"
    assert f(_c("INDETERMINATE", ["X"]), _c("NOT_COMPARABLE", [])) == "reversed"
    # disjoint layer-1 sets
    assert f(_c("TIE", ["X", "W"]), _c("TIE", ["Y", "Z"])) == "reversed"


def test_classify_membership_changed_and_purity():
    f = panel_v3.classify_resolution_change
    assert f(_c("TIE", ["X", "Y"]), _c("TIE", ["X", "Z"])) == "membership_changed"
    assert f(_c("TIE", ["X", "Y"]), _c(RECOMMEND, ["X"], "X")) == "membership_changed"
    assert f(_c("INDETERMINATE", ["X"]), _c("TIE", ["X", "Y"])) == "membership_changed"
    # Two EMPTY layer-1 sets are not a "disjoint" reversal (no nearest unit either side).
    assert f(_c("NOT_COMPARABLE", []), _c("BLOCKED", [])) == "membership_changed"
    raw, m = _c("TIE", ["X", "Y"]), _c(RECOMMEND, ["X"], "X")
    before = copy.deepcopy((raw, m))
    assert {f(raw, m) for _ in range(3)} == {"membership_changed"}
    assert (raw, m) == before                                    # pure: inputs untouched


def test_classify_error():
    f = panel_v3.classify_resolution_change
    assert f(_c("ERROR", []), _c(RECOMMEND, ["X"], "X")) == "error"
    assert f(_c(RECOMMEND, ["X"], "X"), _c("ERROR", [])) == "error"
    assert f(_c(RECOMMEND, ["X"], "X"), None) == "error"
    assert f(None, _c(RECOMMEND, ["X"], "X")) == "error"


# --------------------------------------------------------------------------- #
# FABRICATED panels for rule-level tests.                                      #
#                                                                              #
# Candidates B1, B2 (basaltic) and C1, C2 (smooth_control). Each cell kind is a #
# set of made-up distance vectors (smaller = closer); frontier.summarize turns  #
# them into a consistent layer 1 + dominance matrix:                           #
#   "S": C1 nearest and dominating all      -> S satisfied, V not;             #
#   "V": B1 nearest and dominating C1 and C2 -> V satisfied, S not;            #
#   "N": B1 beats only C1, B2 beats only C2  -> layer 1 {B1, B2}; neither.     #
# --------------------------------------------------------------------------- #
_FAKE_CLASSES = {"B1": "basaltic", "B2": "basaltic", "C1": "smooth_control",
                 "C2": "smooth_control"}
_VECS = {"S": {"C1": [1, 1], "C2": [2, 2], "B1": [5, 5], "B2": [6, 6]},
         "V": {"B1": [1, 1], "B2": [2, 2], "C1": [5, 5], "C2": [6, 6]},
         "N": {"B1": [1, 3], "B2": [3, 1], "C1": [2, 4], "C2": [4, 2]}}
_FAKE_SUPPORTS = (240.0, 360.0)
_FAKE_REFS = (("p1", "volcanic_plains", "confirmatory"),
              ("p2", "volcanic_plains", "confirmatory"),
              ("p3", "volcanic_plains", "confirmatory"),
              ("h1", "highland", "confirmatory"),
              ("h2", "highland", "confirmatory"),
              ("p_expl", "volcanic_plains", "exploratory"),
              ("calib", "contrast", "exploratory"))


def _fake_cell(spec, s):
    if spec == "ERROR":
        return {"support_m": s, "result_state": "ERROR", "recommended_unit": None,
                "pareto_layer1": [], "pareto_layers": [], "dominance_matrix": {},
                "error": "RuntimeError: injected"}
    kind, state = (spec, None) if isinstance(spec, str) else spec
    fr = frontier.summarize(_VECS[kind])
    layer1 = list(fr["pareto_layers"][0])
    state = state or (RECOMMEND if len(layer1) == 1 else "TIE")
    return {"support_m": s, "result_state": state,
            "recommended_unit": layer1[0] if state == RECOMMEND else None,
            "pareto_layer1": layer1, "pareto_layers": fr["pareto_layers"],
            "dominance_matrix": fr["dominance_matrix"]}


def _fake_panel(world, expects=None, refs=_FAKE_REFS):
    """``world``: {ref_id: one cell spec per support}; refs absent from it are dropped.
    Named expectations are evaluated by the real ``confirmation.evaluate_expectation``."""
    out = []
    for rid, cls, status in refs:
        if rid not in world:
            continue
        cells = [_fake_cell(spec, s) for spec, s in zip(world[rid], _FAKE_SUPPORTS)]
        exps = (expects or {}).get(rid, [_S, _V])
        out.append({"id": rid, "class": cls, "status": status, "cells": cells,
                    "expectations": {e["name"]: cf.evaluate_expectation(
                        copy.deepcopy(e), cells, _FAKE_CLASSES) for e in exps}})
    return {"references": out, "supports_m": list(_FAKE_SUPPORTS)}


# The two fabricated worlds: plains S-like / V-like; highlands S-like in both.
_SMOOTH_WORLD = {rid: ["S", "S"] for rid, *_ in _FAKE_REFS}
_SPECIFIC_WORLD = dict(_SMOOTH_WORLD, p1=["V", "V"], p2=["V", "V"], p3=["V", "V"])


def _verdicts(hyp):
    return {k: hyp[k]["verdict"] for k in ("S", "V", "R")}


def test_rule_boundaries_on_fabricated_cells():
    ev = panel_v3.evaluate_v3_hypotheses
    smooth, spec = _fake_panel(_SMOOTH_WORLD), _fake_panel(_SPECIFIC_WORLD)
    assert _verdicts(ev(smooth, smooth, [])) == {
        "S": "supported", "V": "not_supported", "R": "supported"}
    assert _verdicts(ev(spec, spec, [])) == {
        "S": "not_supported", "V": "supported", "R": "supported"}
    # S: exactly 2 of 3 holding is enough; "mixed" is not "holds"; <= 1 is not.
    two = dict(_SMOOTH_WORLD, p3=["S", "N"])
    assert ev(_fake_panel(two), None, [])["S"]["verdict"] == "supported"
    one = dict(two, p2=["N", "N"])
    assert ev(_fake_panel(one), None, [])["S"]["verdict"] == "not_supported"
    # V: 2 of 3 plains hold is enough ...
    v2 = dict(_SPECIFIC_WORLD, p3=["V", "N"])
    assert ev(_fake_panel(v2), None, [])["V"]["verdict"] == "supported"
    # ... but not if only 1 does ...
    v1 = dict(v2, p2=["N", "N"])
    assert ev(_fake_panel(v1), None, [])["V"]["verdict"] == "not_supported"
    # ... nor if V ALSO holds for both highlands (not specific to plains).
    gen = dict(_SPECIFIC_WORLD, h1=["V", "V"], h2=["V", "V"])
    out = ev(_fake_panel(gen), None, [])["V"]
    assert out["verdict"] == "not_supported" and "not specific" in out["reason"], out
    # ... while one highland with V "mixed" is already "not holds".
    one_h = dict(gen, h2=["V", "N"])
    assert ev(_fake_panel(one_h), None, [])["V"]["verdict"] == "supported"
    # Neither world: plains "N" everywhere.
    neither = dict(_SMOOTH_WORLD, p1=["N", "N"], p2=["N", "N"], p3=["N", "N"])
    h = ev(_fake_panel(neither), None, [])
    assert (h["S"]["verdict"], h["V"]["verdict"]) == ("not_supported", "not_supported")
    for k in ("S", "V", "R"):
        assert h[k]["rule"] == panel_v3.RULES_V3[k] and h[k]["rule"].startswith(k + " ")


def test_r_rule_reversal_vs_stabilisation():
    ev = panel_v3.evaluate_v3_hypotheses
    # The v2 pattern: raw INDETERMINATE with sole layer 1 {B1} -> matched RECOMMEND B1.
    raw = _fake_panel(dict(_SPECIFIC_WORLD, p1=[("V", "INDETERMINATE")] * 2,
                           p2=[("V", "INDETERMINATE")] * 2))
    r = ev(raw, _fake_panel(_SPECIFIC_WORLD), [])["R"]
    assert r["verdict"] == "supported", r
    assert r["counts"]["stabilised"] == 4 and r["counts"]["reversed"] == 0, r["counts"]
    # A real reversal (nearest B1 -> nearest C1) in one confirmatory cell.
    rev = ev(_fake_panel(_SPECIFIC_WORLD),
             _fake_panel(dict(_SPECIFIC_WORLD, p2=["V", "S"])), [])["R"]
    assert rev["verdict"] == "not_supported" and rev["counts"]["reversed"] == 1, rev
    assert rev["evidence"]["reversed_cells"] == ["p2@360 m"], rev["evidence"]
    # A reversal in an EXPLORATORY reference is reported, never counted.
    expl = ev(_fake_panel(_SPECIFIC_WORLD),
              _fake_panel(dict(_SPECIFIC_WORLD, p_expl=["V", "V"], calib=["V", "V"])), [])["R"]
    assert expl["verdict"] == "supported", expl
    assert expl["not_counted"]["counts"]["reversed"] == 4, expl["not_counted"]["counts"]
    # No resolution control -> inconclusive, never silently "supported".
    nr = ev(_fake_panel(_SPECIFIC_WORLD), None, [])["R"]
    assert nr["verdict"] == "inconclusive" and "not run" in nr["reason"], nr


def test_exploratory_and_calibration_refs_never_counted():
    ev = panel_v3.evaluate_v3_hypotheses
    # Confirmatory plains fail S; exploratory plains + calibration HOLD it: no rescue.
    world = dict(_SPECIFIC_WORLD, p_expl=["S", "S"], calib=["S", "S"])
    h = ev(_fake_panel(world), None, [])
    assert h["S"]["verdict"] == "not_supported", h["S"]
    assert sorted(h["S"]["evidence"]) == ["p1", "p2", "p3"]
    assert h["S"]["not_counted"]["p_expl"]["outcome"] == "holds"
    assert h["S"]["not_counted"]["p_expl"]["counts_as_confirmation"] is False
    # Confirmatory plains fail V; exploratory plains + calibration HOLD it: no rescue.
    world = dict(_SMOOTH_WORLD, p_expl=["V", "V"], calib=["V", "V"])
    h = ev(_fake_panel(world), None, [])
    assert h["V"]["verdict"] == "not_supported", h["V"]
    assert sorted(h["V"]["evidence"]) == ["h1", "h2", "p1", "p2", "p3"]
    assert {k for k, v in h["V"]["not_counted"].items()} == {"p_expl", "calib"}


def test_wrong_reference_counts_inconclusive():
    ev = panel_v3.evaluate_v3_hypotheses
    no_p3 = {k: v for k, v in _SMOOTH_WORLD.items() if k != "p3"}
    h = ev(_fake_panel(no_p3), None, [])
    assert h["S"]["verdict"] == "inconclusive" and "exactly 3" in h["S"]["reason"], h["S"]
    assert h["V"]["verdict"] == "inconclusive", h["V"]
    no_h2 = {k: v for k, v in _SPECIFIC_WORLD.items() if k != "h2"}
    h = ev(_fake_panel(no_h2), None, [])
    assert h["S"]["verdict"] == "not_supported"            # S does not read highlands
    assert h["V"]["verdict"] == "inconclusive" and "exactly 3 and 2" in h["V"]["reason"]
    # A 4th confirmatory plains reference is also outside the frozen rule.
    extra = _FAKE_REFS + (("p4", "volcanic_plains", "confirmatory"),)
    h = ev(_fake_panel(dict(_SMOOTH_WORLD, p4=["S", "S"]), refs=extra), None, [])
    assert h["S"]["verdict"] == "inconclusive" and h["S"]["counts"]["confirmatory_plains_refs"] == 4
    assert ev(None, None, [])["S"]["verdict"] == "inconclusive"


def test_injected_error_inconclusive():
    ev = panel_v3.evaluate_v3_hypotheses
    err = _fake_panel(dict(_SMOOTH_WORLD, p2=["S", "ERROR"]))
    h = ev(err, err, [])
    for k in ("S", "V", "R"):
        assert h[k]["verdict"] == "inconclusive" and "ERROR" in h[k]["reason"].upper(), h[k]
    # An ERROR in a highland cell leaves S (plains only) evaluable, but not V.
    herr = _fake_panel(dict(_SPECIFIC_WORLD, h1=["ERROR", "S"]))
    h = ev(herr, None, [])
    assert h["S"]["verdict"] == "not_supported" and h["V"]["verdict"] == "inconclusive"
    # An ERROR only in the resolution-matched run makes R (only) inconclusive.
    ok = _fake_panel(_SPECIFIC_WORLD)
    h = ev(ok, _fake_panel(dict(_SPECIFIC_WORLD, h2=["S", "ERROR"])), [])
    assert _verdicts(h) == {"S": "not_supported", "V": "supported", "R": "inconclusive"}
    assert h["R"]["counts"]["error"] == 1


def test_misdeclared_expectation_inconclusive():
    ev = panel_v3.evaluate_v3_hypotheses
    other = {"name": "S", "type": "class_in_layer1", "class": "basaltic"}
    h = ev(_fake_panel(_SMOOTH_WORLD, expects={"p1": [other, _V]}), None, [])
    assert h["S"]["verdict"] == "inconclusive" and "does not apply" in h["S"]["reason"], h["S"]
    h = ev(_fake_panel(_SPECIFIC_WORLD, expects={"h2": [_S]}), None, [])   # V missing
    assert h["V"]["verdict"] == "inconclusive" and "['h2']" in h["V"]["reason"], h["V"]


def test_comparability_violation_inconclusive_rule_verdict_kept():
    ev = panel_v3.evaluate_v3_hypotheses
    spec = _fake_panel(_SPECIFIC_WORLD)
    h = ev(spec, spec, [{"run": "raw", "reference": "p1", "support_m": 240.0,
                         "regime": "footprint-mismatched", "issues": ["i"]}])
    assert _verdicts(h) == {"S": "inconclusive", "V": "inconclusive", "R": "inconclusive"}
    assert {k: h[k]["rule_verdict"] for k in ("S", "V", "R")} == {
        "S": "not_supported", "V": "supported", "R": "supported"}
    assert "honest-regime violation in 1" in h["V"]["reason"], h["V"]
    assert h["reading"].startswith("neither explanation supported"), h["reading"]
    # Robustness info compares the RULE verdicts, untouched by the gate.
    assert h["robustness_info"]["V"]["raw_rule_verdict"] == "supported", h["robustness_info"]
    # The gate reads CONFIRMATORY references only (raw + matched); "+low-power" allowed.
    def with_regime(panel, regimes):
        panel = copy.deepcopy(panel)
        for r in panel["references"]:
            for c in r["cells"]:
                reg = regimes.get(r["id"], "honest")
                c["comparability"] = {"regime": reg, "assessment": {"issues": ["x"]}}
        return panel
    p = with_regime(spec, {"calib": "footprint-mismatched", "p_expl": "below-effective-resolution",
                           "h1": "honest+low-power"})
    viol, low, _ = matched_real._regime_audit([("raw", panel_v3._confirmatory_view(p))])
    assert viol == [] and len(low) == 2, (viol, low)
    p = with_regime(spec, {"h2": "footprint-mismatched+low-power"})
    viol, _, _ = matched_real._regime_audit([("raw", panel_v3._confirmatory_view(p))])
    assert [v["reference"] for v in viol] == ["h2", "h2"], viol


def test_robustness_info_and_reading():
    ev = panel_v3.evaluate_v3_hypotheses
    smooth, spec = _fake_panel(_SMOOTH_WORLD), _fake_panel(_SPECIFIC_WORLD)
    h = ev(spec, smooth, [])                      # matched run looks like the other world
    ri = h["robustness_info"]
    assert ri["evaluated"] is True and "not a hypothesis" in ri["label"]
    assert ri["S"] == {"raw_rule_verdict": "not_supported",
                       "resolution_matched_rule_verdict": "supported",
                       "resolution_matched_reason": ri["S"]["resolution_matched_reason"],
                       "differs": True}, ri["S"]
    assert ri["V"]["differs"] is True and ri["any_differs"] is True
    assert h["R"]["verdict"] == "not_supported"   # B1 -> C1 nearest: a reversal
    assert ev(spec, None, [])["robustness_info"]["evaluated"] is False
    assert ev(smooth, smooth, [])["reading"].startswith(
        "smoothness/shortlist explanation supported: ")
    assert ev(spec, spec, [])["reading"].startswith("volcanic-specific signal supported: ")
    neither = dict(_SMOOTH_WORLD, p1=["N", "N"], p2=["N", "N"], p3=["N", "N"])
    assert ev(_fake_panel(neither), None, [])["reading"].startswith(
        "neither explanation supported by the pre-declared rules")


# --------------------------------------------------------------------------- #
# GROUND-TRUTH scenes on the real engine.                                      #
#                                                                              #
# Terrain = Gaussian-correlated noise (resolution.gaussian_filter_nan of a     #
# seeded white field), unit std times an amplitude, so most relief sits at     #
# wavelengths longer than the 180 m effective-resolution target (as on real    #
# terrain):                                                                    #
#   basaltic       amp 10 m, correlation sigma 6 px (hummocky)                  #
#   smooth_control amp  1 m, correlation sigma 10 px (gentle)                   #
#   rough_control  amp 60 m, correlation sigma 3 px                             #
# Earth candidates: 220 px at 30 m (6.6 km). Mars references are a 30 m field  #
# of a given kind, 2x2 block-averaged to 60 m (a coarser sensor): 110 px.      #
# Support floor = 3 x 60 = 180 m; honest 240 / 360 m; diagnostic 120 m.        #
#                                                                              #
#   Scene A, SMOOTHNESS world: every confirmatory Mars reference is smooth     #
#   -> a smooth control is nearest for plains (S holds) and no basaltic        #
#   candidate dominates the smooth controls (V fails) => S supported, V not.   #
#   Scene B, SPECIFIC world: plains references are basaltic-like, highlands    #
#   smooth -> a basaltic candidate dominates both smooth controls for plains   #
#   and not for highlands => V supported, S not.                                #
#                                                                              #
# Each scene also carries an EXPLORATORY plains reference that behaves like    #
# the OTHER world and a calibration reference -- neither may be counted.       #
# Frozen after exploration: the per-reference S/V outcomes were identical       #
# across 3 seed sets x reference amplitude x0.7 / x1.0 / x1.4 (18 variants).   #
# --------------------------------------------------------------------------- #
_CAND_DX, _REF_DX = 30.0, 60.0
_N_CAND, _N_REF = 220, 110
_HONEST, _DIAG = [240.0, 360.0], [120.0]
_KINDS = {"basaltic": (10.0, 6.0), "smooth": (1.0, 10.0), "rough": (60.0, 3.0)}
_CANDS = (("earth_basalt_a", "basaltic", 10.0, 6.0, 101),
          ("earth_basalt_b", "basaltic", 20.0, 6.0, 102),
          ("earth_smooth_a", "smooth_control", 1.0, 10.0, 103),
          ("earth_smooth_b", "smooth_control", 2.0, 10.0, 104),
          ("earth_rough", "rough_control", 60.0, 3.0, 105))
_CONF_PLAINS = ["mars_plains_1", "mars_plains_2", "mars_plains_3"]
_CONF_HIGH = ["mars_highland_1", "mars_highland_2"]
_SCENE_REFS = (  # id, class, status, seed, kind in scene A, kind in scene B
    ("mars_plains_1", "volcanic_plains", "confirmatory", 11, "smooth", "basaltic"),
    ("mars_plains_2", "volcanic_plains", "confirmatory", 12, "smooth", "basaltic"),
    ("mars_plains_3", "volcanic_plains", "confirmatory", 13, "smooth", "basaltic"),
    ("mars_highland_1", "highland", "confirmatory", 21, "smooth", "smooth"),
    ("mars_highland_2", "highland", "confirmatory", 22, "smooth", "smooth"),
    ("mars_plains_expl", "volcanic_plains", "exploratory", 31, "basaltic", "smooth"),
    ("mars_calibration", "calibration_contrast", "exploratory", 41, "rough", "rough"),
)


def _field(n, amp, corr_px, seed):
    z = resolution.gaussian_filter_nan(synthetic.rough_field((n, n), 1.0, seed), corr_px)
    z = z - z.mean()
    return amp * z / z.std()


def _scene(world, **cfg_over):
    """-> (grids, spacings, rights, cfg) for world "A" (smoothness) or "B" (specific)."""
    grids, spacings = {}, {}
    for uid, _cls, amp, corr, seed in _CANDS:
        grids[uid], spacings[uid] = _field(_N_CAND, amp, corr, seed), _CAND_DX
    panel = []
    for rid, cls, status, seed, kind_a, kind_b in _SCENE_REFS:
        amp, corr = _KINDS[kind_a if world == "A" else kind_b]
        z = _field(2 * _N_REF, amp, corr, seed)
        grids[rid] = z.reshape(_N_REF, 2, _N_REF, 2).mean(axis=(1, 3))
        spacings[rid] = _REF_DX
        panel.append({"id": rid, "class": cls, "status": status,
                      "expects": [dict(_S), dict(_V)]})
    rights = {u: "verified_allowed" for u in grids}
    cfg = {"experiment": "matched_footprint_panel_v3", "extent_m": 6000.0,
           "extent_policy": "min_available", "honest_supports_m": list(_HONEST),
           "diagnostic_supports_m": list(_DIAG), "res_factor": 3.0,
           "resolution_control": True, "adequacy": True, "adequacy_support_m": 240.0,
           "adversarial": True, "primary_reference": "mars_plains_1",
           "min_valid_fraction": 0.5, "seed": 0,
           "candidates": [c[0] for c in _CANDS],
           "candidate_classes": {c[0]: c[1] for c in _CANDS}, "panel": panel}
    cfg.update(cfg_over)
    return grids, spacings, rights, cfg


_CACHE = {}


def _scene_bundle(world):
    if world not in _CACHE:
        g, sp, rt, cfg = _scene(world)
        with contextlib.redirect_stdout(io.StringIO()):
            _CACHE[world] = panel_v3.run_panel_v3_from_grids(g, sp, rt, cfg)
    return _CACHE[world]


def _outcomes(bundle, name):
    return {r["id"]: r["expectations"][name]["outcome"]
            for r in bundle["panel_raw"]["honest"]["references"]}


def test_scene_a_smoothness_world_s_supported_v_not():
    b = _scene_bundle("A")
    h = b["hypotheses"]
    assert h["S"]["verdict"] == "supported", h["S"]["reason"]
    assert h["S"]["counts"]["holds_ids"] == _CONF_PLAINS
    assert h["V"]["verdict"] == "not_supported", h["V"]["reason"]
    assert h["V"]["counts"]["plains_holds"] == 0
    assert h["reading"].startswith("smoothness/shortlist explanation supported: ")
    # The pattern behind it: a smooth control is in layer 1 of EVERY confirmatory cell.
    for r in b["panel_raw"]["honest"]["references"]:
        if r["status"] == "confirmatory":
            for c in r["cells"]:
                assert {"earth_smooth_a", "earth_smooth_b"} & set(c["pareto_layer1"]), c
    # Honest regime everywhere, nothing demoted, footprint as requested.
    assert b["regime_violation"]["flag"] is False
    assert b["footprint"]["extent_m"] == 6000.0 and b["footprint"]["policy"] == "min_available"
    assert b["supports"]["honest_m"] == _HONEST and b["support_floor"]["floor_m"] == 180.0


def test_scene_b_specific_world_v_supported_s_not():
    b = _scene_bundle("B")
    h = b["hypotheses"]
    assert h["V"]["verdict"] == "supported", h["V"]["reason"]
    assert h["V"]["counts"]["plains_holds_ids"] == _CONF_PLAINS
    assert h["V"]["counts"]["highland_not_holds_ids"] == _CONF_HIGH
    assert h["S"]["verdict"] == "not_supported", h["S"]["reason"]
    assert h["reading"].startswith("volcanic-specific signal supported: ")
    oc = _outcomes(b, "V")
    assert [oc[r] for r in _CONF_PLAINS] == ["holds"] * 3
    assert [oc[r] for r in _CONF_HIGH] == ["fails"] * 2


def test_scenes_r_robustness_info_and_bundle_shape():
    for world in ("A", "B"):
        b = _scene_bundle(world)
        h = b["hypotheses"]
        assert h["R"]["verdict"] == "supported", (world, h["R"]["reason"])
        assert h["R"]["counts"]["reversed"] == 0 and h["R"]["counts"]["error"] == 0
        assert sum(h["R"]["counts"].values()) == 5 * len(_HONEST)   # confirmatory cells
        ri = h["robustness_info"]
        assert ri["evaluated"] is True and ri["any_differs"] is False, ri
        rc = b["resolution_control"]
        assert rc["run"] is True and rc["target_fwhm_m"] == 3.0 * _REF_DX
        assert {r["support_class"] for r in rc["classification"]} == {"honest", "diagnostic"}
        assert all(r["change"] in panel_v3.CHANGE_CLASSES for r in rc["classification"])
        # Diagnostic cells are labelled, never "honest", never evidence.
        for r in b["panel_raw"]["diagnostic"]["references"]:
            for c in r["cells"]:
                assert c["comparability"]["regime"].startswith("below-effective-resolution")
        assert all(not r["counted"] for r in rc["classification"]
                   if r["support_class"] == "diagnostic")
        assert b["candidate_classes"]["earth_rough"] == "rough_control"
        adv = b["primary"]["adversarial"]
        assert adv["evidence_status"].startswith("exploratory") and adv["seed"] == 0, adv
        ade = b["adequacy"]["report"]["per_reference"]
        assert set(ade) == {r[0] for r in _SCENE_REFS} and b["adequacy"]["support_m"] == 240.0
        assert len(b["limitations"]) == len(panel_v3.LIMITATIONS_V3)
        json.dumps(b, sort_keys=True, allow_nan=False)
    # The SPECIFIC world reproduces the v2 situation on its own: INDETERMINATE with
    # the basaltic twin as sole layer-1 unit -> stable RECOMMEND of it. Stabilised,
    # not reversed -- so R is supported where v2's H3 read "not supported".
    assert _scene_bundle("B")["hypotheses"]["R"]["counts"]["stabilised"] >= 1


def test_scene_exploratory_and_calibration_refs_never_counted():
    for world, other in (("A", "V"), ("B", "S")):
        b = _scene_bundle(world)
        h = b["hypotheses"]
        # The exploratory plains reference behaves like the OTHER world ...
        assert _outcomes(b, other)["mars_plains_expl"] == "holds", world
        # ... and is never counted, nor is the calibration reference.
        for k in ("S", "V"):
            assert "mars_plains_expl" not in h[k]["evidence"]
            assert "mars_calibration" not in h[k]["evidence"]
            assert h[k]["not_counted"]["mars_plains_expl"]["counts_as_confirmation"] is False
        assert all(r["reference"] not in ("mars_plains_expl", "mars_calibration")
                   for r in h["R"]["evidence"]["rows"])


# --------------------------------------------------------------------------- #
# Front door, script dispatch, gated hash                                      #
# --------------------------------------------------------------------------- #
def test_run_real_panel_v3_end_to_end_monkeypatched_and_deterministic():
    g, sp, rt, cfg = _scene("A", adversarial=False, adequacy=False, diagnostic_supports_m=[])
    cfg["units"] = [{"id": u} for u in g]
    tmp = tempfile.mkdtemp(prefix="mf_panel_v3_test_")
    cfg_file, proto_file = os.path.join(tmp, "v3.yml"), os.path.join(tmp, "PROTOCOL-v3.md")
    for path, text in ((cfg_file, "experiment: matched_footprint_panel_v3\n"),
                       (proto_file, "# frozen v3\n")):
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
    cfg.update(_config_path=cfg_file, protocol_path=proto_file)
    seen = []
    original = matched_real.load_panel_grids
    matched_real.load_panel_grids = lambda c: (seen.append(c), (g, sp, rt))[1]
    try:
        bufs = [io.StringIO(), io.StringIO()]
        with contextlib.redirect_stdout(bufs[0]):
            first = panel_v3.run_real_panel_v3(cfg, out=os.path.join(tmp, "out"))
        with contextlib.redirect_stdout(bufs[1]):
            second = panel_v3.run_real_panel_v3(cfg, out=None)
        path = os.path.join(tmp, "out", "matched_panel_v3_real.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        assert on_disk == json.loads(json.dumps(first))
        assert json.dumps(first, sort_keys=True, allow_nan=False) == json.dumps(
            second, sort_keys=True, allow_nan=False)                    # deterministic
        assert seen == [cfg, cfg]
        assert on_disk["experiment"] == "matched_footprint_panel_v3"
        assert on_disk["hypotheses"]["S"]["verdict"] == "supported"
        for key, f in (("config", cfg_file), ("protocol", proto_file)):
            with open(f, "rb") as fh:
                assert on_disk[key] == {"path": f, "sha256": hashlib.sha256(fh.read()).hexdigest()}
        assert not any("protocol_path" in w for w in on_disk["warnings"])
        text = bufs[0].getvalue()
        assert text.isascii(), text
        for needle in ("S smoothness/shortlist", "V volcanic specificity",
                       "R resolution robustness", "READING:", "LIMITATIONS", "S+", "V-",
                       "counts_as_confirmation=True", "[bundle] wrote"):
            assert needle in text, needle
    finally:
        matched_real.load_panel_grids = original
        shutil.rmtree(tmp, ignore_errors=True)
    # Without a protocol path the bundle says so instead of inventing one.
    g, sp, rt, lean = _scene("A", adversarial=False, adequacy=False, diagnostic_supports_m=[],
                             resolution_control=False)
    with contextlib.redirect_stdout(io.StringIO()):
        b = panel_v3.run_panel_v3_from_grids(g, sp, rt, lean)
    assert b["protocol"] == {"path": None, "sha256": None}
    assert any("protocol_path" in w for w in b["warnings"])
    assert b["hypotheses"]["R"]["verdict"] == "inconclusive"


def _load_script():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "run_matched_benchmark_under_test_v3",
        os.path.join(root, "scripts", "run_matched_benchmark.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_dispatch_routes_v3_v2_v1_and_honest_block():
    script = _load_script()
    calls = []
    original = (panel_v3.run_real_panel_v3, matched_real.run_real_panel,
                matched_real.run_real_matched)
    panel_v3.run_real_panel_v3 = lambda c, out=None: (calls.append(("v3", c, out)), "v3")[1]
    matched_real.run_real_panel = lambda c, out=None: (calls.append(("v2", c, out)), "v2")[1]
    matched_real.run_real_matched = lambda c, out=None: (calls.append(("v1", c, out)), "v1")[1]

    def blocked(c, out=None):
        raise ImportError("rasterio missing")
    try:
        v3 = {"experiment": "matched_footprint_panel_v3", "panel": [], "units": []}
        assert script.dispatch(v3, "o3", config_path="v3.yml") == "v3"   # BEFORE the panel check
        assert calls[-1][0] == "v3" and calls[-1][2] == "o3"
        assert calls[-1][1]["_config_path"] == "v3.yml" and "_config_path" not in v3
        assert script.dispatch({"panel": [], "units": []}, "o2", config_path="c.yml") == "v2"
        assert calls[-1][1]["config_path"] == "c.yml"
        assert script.dispatch({"experiment": "matched_footprint_panel_v2", "panel": []},
                               "o2") == "v2"
        assert script.dispatch({"reference_id": "r", "units": []}, "o1") == "v1"
        assert [c[0] for c in calls] == ["v3", "v2", "v2", "v1"]
        for cfg, mod, runner, needle in (
                (v3, panel_v3, "run_real_panel_v3", "v3"),
                ({"panel": [{"id": "r"}]}, matched_real, "run_real_panel",
                 "BENCHMARK-PROTOCOL-v2.md"),
                ({"reference_id": "r"}, matched_real, "run_real_matched",
                 "matched_footprint.example.yml")):
            setattr(mod, runner, blocked)
            script._load_config = lambda path, cfg=cfg: cfg
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = script.main(["--config", "x.yml", "--out", "unused"])
            assert code == 2 and "BLOCKED" in buf.getvalue() and needle in buf.getvalue()
        assert "panel_v3.run_real_panel_v3" in script._RASTERIO_BLOCKED_V3
    finally:
        (panel_v3.run_real_panel_v3, matched_real.run_real_panel,
         matched_real.run_real_matched) = original


def test_gated_study_hash_unchanged():
    """Gated: the default study package hash is 64 lowercase hex and identical across
    two calls (this module perturbs no shared state). Never pinned to a literal."""
    h1 = study.run_study()["package_hash"]
    h2 = study.run_study()["package_hash"]
    assert len(h1) == 64 and all(c in "0123456789abcdef" for c in h1), h1
    assert h1 == h2
