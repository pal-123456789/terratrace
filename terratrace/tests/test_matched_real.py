"""REAL matched-footprint experiment wiring, exercised WITHOUT rasterio or network.

``matched_real.run_real_matched`` is what the user runs on the data machine, but its
only rasterio step is isolated in ``matched_real.load_metric_grids``. Here we never
call that loader: we build SYNTHETIC per-body metric grids (the validated rough-core-
in-smooth-apron fixture, all at 30 m spacing) and drive ``run_from_grids`` -- the pure
core -- directly, exactly as tests/test_real_study_path.py substitutes synthetic
arrays for ``study.load_real_units``. One test additionally monkeypatches
``load_metric_grids`` and drives ``run_real_matched`` end to end to prove the wiring,
still with no rasterio.

The scene reproduces the footprint confound the real experiment must survive: the
reference is a ROUGH core (amp 25) inside a SMOOTH apron (amp 4); A_smooth is smooth
everywhere (amp 4), B_rough rough everywhere (amp 25). At the CORE extent the matched
decision must pick B_rough; at a LARGE extent the apron dominates and it must pick
A_smooth -- the extent dependence that a matched footprint controls and a mismatched
footprint does not.

The v2 REFERENCE PANEL (docs/BENCHMARK-PROTOCOL-v2.md) is tested the same way: a
synthetic panel with KNOWN answers drives ``run_panel_from_grids``, and the rasterio
seam ``load_panel_grids`` is only ever monkeypatched, never called.
"""
import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile

import numpy as np

from terratrace import matched_real, synthetic, study, reproject
from terratrace import confirmation as cf

# Frozen synthetic scene (identical ground truth to tests/test_matched_benchmark.py
# and scripts/run_matched_benchmark.py).
_N = 400
_DX = 30.0
_CORE_RADIUS_M = 700.0
_CORE_EXTENT = 1200.0     # ~ the rough core -> B_rough is the correct analog
_LARGE_EXTENT = 12000.0   # whole scene -> smooth apron dominates -> A_smooth
_REP_SUPPORT = 90.0


def _scene():
    ii, jj = np.indices((_N, _N))
    r = np.hypot(ii - _N // 2, jj - _N // 2) * _DX
    core = r < _CORE_RADIUS_M
    X = synthetic.rough_field((_N, _N), amplitude=25.0, seed=1)
    Y = synthetic.rough_field((_N, _N), amplitude=4.0, seed=1)
    grids = {"ref": np.where(core, X, Y),
             "A_smooth": synthetic.rough_field((_N, _N), amplitude=4.0, seed=2),
             "B_rough": synthetic.rough_field((_N, _N), amplitude=25.0, seed=3)}
    spacings = {uid: _DX for uid in grids}
    rights = {uid: "verified_allowed" for uid in grids}
    return grids, spacings, rights


def test_extent_dependence_core_lens():
    """Core extent -> B_rough; large extent -> A_smooth (the validated confound)."""
    grids, spacings, rights = _scene()
    core = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _CORE_EXTENT, [_REP_SUPPORT],
        decision_metrics_list=("core",), n_boot=0)
    large = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _LARGE_EXTENT, [_REP_SUPPORT],
        decision_metrics_list=("core",), n_boot=0)
    assert core["matched_primary"]["recommended_unit"] == "B_rough"
    assert core["matched_recommendation_by_support"][f"{_REP_SUPPORT:g}"] == "B_rough"
    assert large["matched_primary"]["recommended_unit"] == "A_smooth"
    assert large["matched_recommendation_by_support"][f"{_REP_SUPPORT:g}"] == "A_smooth"


def test_bundle_keys_and_json_serialisable():
    """The bundle is JSON-serialisable and carries the expected top-level keys."""
    grids, spacings, rights = _scene()
    bundle = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _CORE_EXTENT, [_REP_SUPPORT, 150.0],
        decision_metrics_list=("core", "extended"), n_boot=20)
    expected = {"supports_m", "cells", "stability_grid", "baselines", "lens_ablation",
                "provenance", "matched_primary", "matched_recommendation_by_support",
                "mismatched", "confound_verdict", "bootstrap_nondomination",
                "scope_note", "prohibited_claims"}
    assert expected <= set(bundle)
    # JSON round-trips (no numpy scalars / arrays leaked into the bundle).
    s = json.dumps(bundle, sort_keys=True)
    assert json.loads(s)["reference_id"] == "ref"
    # Non-domination present because n_boot>0, and the firewall is carried.
    assert bundle["bootstrap_nondomination"] is not None
    assert isinstance(bundle["prohibited_claims"], list) and bundle["prohibited_claims"]
    # Each stability cell exposes its support and recommendation.
    assert {c["support_m"] for c in bundle["cells"]} == {_REP_SUPPORT, 150.0}


def test_determinism():
    """Two runs on identical inputs produce byte-identical bundles (seed-fixed)."""
    grids, spacings, rights = _scene()
    kw = dict(decision_metrics_list=("core", "extended"), n_boot=20)
    a = matched_real.run_from_grids(grids, spacings, rights, "ref", _CORE_EXTENT,
                                    [_REP_SUPPORT], **kw)
    b = matched_real.run_from_grids(grids, spacings, rights, "ref", _CORE_EXTENT,
                                    [_REP_SUPPORT], **kw)
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def test_single_and_multiple_supports():
    """run_from_grids handles a single support and a multi-support scale sweep."""
    grids, spacings, rights = _scene()
    one = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _CORE_EXTENT, [_REP_SUPPORT],
        decision_metrics_list=("core",), n_boot=0)
    many = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _CORE_EXTENT, [_REP_SUPPORT, 150.0],
        decision_metrics_list=("core",), n_boot=0)
    assert len(one["cells"]) == 1
    assert one["supports_m"] == [_REP_SUPPORT]
    assert len(many["cells"]) == 2
    assert many["supports_m"] == [_REP_SUPPORT, 150.0]
    # Each cell is a matched cell at the FIXED extent.
    assert all(c["extent_m"] == _CORE_EXTENT and c["mode"] == "matched"
               for c in many["cells"])


def test_mismatched_control_available_and_flips():
    """At the core extent the mismatched control is available and the footprint
    mismatch alone flips the recommendation (B_rough -> A_smooth)."""
    grids, spacings, rights = _scene()
    bundle = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _CORE_EXTENT, [_REP_SUPPORT],
        decision_metrics_list=("core",), n_boot=0, mismatch_ratio=10.0)
    mism = bundle["mismatched"]
    assert mism.get("available", True) is not False      # control ran
    assert mism["recommended_unit"] == "A_smooth"
    assert mism["footprint_ratio"] == 10.0
    assert bundle["confound_verdict"]["footprint_confound_changes_result"] is True


def test_mismatched_control_not_available_at_full_extent():
    """At the full-scene extent the reference cannot be cropped larger, so the
    mismatched control reports unavailable rather than silently truncating."""
    grids, spacings, rights = _scene()
    bundle = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _LARGE_EXTENT, [_REP_SUPPORT],
        decision_metrics_list=("core",), n_boot=0)
    assert bundle["mismatched"]["available"] is False
    assert bundle["confound_verdict"]["evaluated"] is False


def test_all_six_lens_ablation():
    """The default six-lens list drives the ablation at the matched footprint; on the
    small core crop every lens evaluates and the core lens recovers B_rough."""
    grids, spacings, rights = _scene()
    bundle = matched_real.run_from_grids(
        grids, spacings, rights, "ref", _CORE_EXTENT, [_REP_SUPPORT],
        decision_metrics_list=("core", "extended", "geomorphic", "landform",
                               "texture", "hydro"), n_boot=0)
    assert set(bundle["lens_ablation"]) == {"core", "extended", "geomorphic",
                                            "landform", "texture", "hydro"}
    assert bundle["lens_ablation"]["core"]["recommended_unit"] == "B_rough"
    assert bundle["decision_metrics_list"] == ["core", "extended", "geomorphic",
                                               "landform", "texture", "hydro"]


def test_center_bbox_geometry():
    """The pure (rasterio-free) window helper centres on the AOI and spans ~extent_m
    in metres, with the longitude span widened by 1/cos(lat)."""
    west, south, east, north = matched_real._center_bbox(226.5, -21.5, 40000.0, "mars")
    assert abs((west + east) / 2.0 - 226.5) < 1e-9
    assert abs((south + north) / 2.0 - (-21.5)) < 1e-9
    m_per_deg = reproject.body_radius_m("mars") * np.pi / 180.0
    assert abs((north - south) * m_per_deg - 40000.0) < 1.0        # lat span ~ extent
    assert (east - west) > (north - south)                        # widened by 1/cos(lat)


def test_run_real_matched_end_to_end_monkeypatched():
    """Monkeypatch the rasterio seam to return synthetic grids and drive
    run_real_matched end to end (bundle written to disk), proving the wiring with no
    rasterio and no yaml."""
    grids, spacings, rights = _scene()
    cfg = {"reference_id": "ref", "extent_m": _CORE_EXTENT,
           "support_sweep_m": [_REP_SUPPORT], "decision_metrics": ["core", "extended"],
           "min_valid_fraction": 0.5, "n_boot": 20,
           "units": [{"id": "ref"}, {"id": "A_smooth"}, {"id": "B_rough"}]}
    tmp = tempfile.mkdtemp(prefix="mf_real_test_")
    original = matched_real.load_metric_grids
    matched_real.load_metric_grids = lambda c: (grids, spacings, rights, "ref")
    try:
        bundle = matched_real.run_real_matched(cfg, out=tmp)
        path = os.path.join(tmp, "matched_benchmark_real.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        assert on_disk["reference_id"] == "ref"
        assert on_disk["matched_primary"]["recommended_unit"] == "B_rough"
        assert bundle["experiment"] == "matched_footprint_real_v1"
        assert bundle["extent_m"] == _CORE_EXTENT
    finally:
        matched_real.load_metric_grids = original
        shutil.rmtree(tmp, ignore_errors=True)


def test_gated_study_hash_unchanged():
    """The synthetic gated study package hash is 64-hex and unchanged across calls
    (this module's new code must not perturb the frozen study path)."""
    h1 = study.run_study()["package_hash"]
    h2 = study.run_study()["package_hash"]
    assert len(h1) == 64 and all(c in "0123456789abcdef" for c in h1)
    assert h1 == h2


def test_select_compared_units_holds_out_same_body_references():
    """A second window on the SAME body as the reference must be HELD OUT of the
    candidate pool (else it trivially dominates every cross-body Earth candidate and
    masks the real question). Earth candidates are compared by default; an explicit
    role='candidate' can override the same-body hold-out."""
    units = [{"id": "mars_daedalia", "body": "mars", "is_reference": True},
             {"id": "mars_elysium", "body": "mars", "role": "held_out_reference"},
             {"id": "earth_a", "body": "earth"},
             {"id": "earth_b", "body": "earth"}]
    compared, held = matched_real.select_compared_units(units, "mars_daedalia")
    assert compared[0] == "mars_daedalia"
    assert set(compared) == {"mars_daedalia", "earth_a", "earth_b"}
    assert held == ["mars_elysium"]
    # same-body unit with NO explicit role is also held out (safe default)
    u2 = [{"id": "ref", "body": "mars", "is_reference": True},
          {"id": "m2", "body": "mars"}, {"id": "e", "body": "earth"}]
    c2, h2 = matched_real.select_compared_units(u2, "ref")
    assert h2 == ["m2"] and set(c2) == {"ref", "e"}
    # explicit role='candidate' keeps a same-body unit in the compared pool
    u3 = [{"id": "ref", "body": "mars", "is_reference": True},
          {"id": "m2", "body": "mars", "role": "candidate"}]
    c3, h3 = matched_real.select_compared_units(u3, "ref")
    assert "m2" in c3 and h3 == []


# --------------------------------------------------------------------------- #
# v2 REFERENCE PANEL -- offline, synthetic, KNOWN answers.                      #
#                                                                               #
# Same ground-truth style as tests/test_confirmation.py: candidates X moderate  #
# (amp 10), Y very smooth (1), Z very rough (60), all at 30 m. The panel        #
# references sit at a COARSER 60 m (MOLA-like), so the support floor is         #
# 3 x 60 = 180 m and the configured honest 150 m support must be DEMOTED.       #
# Plains references are X-like (white noise of amp 5 at 60 m block-averages     #
# like amp 10 at 30 m); contrast references are Z-like. Z's tile (160 px =      #
# 4800 m) is smaller than the requested 6000 m, so the common footprint must    #
# auto-reduce to 4800 m with Z as the limiting unit.                            #
# --------------------------------------------------------------------------- #
_PANEL_REFS = (  # id, class, status, seed
    ("plains_expl_1", "volcanic_plains", "exploratory", 11),
    ("plains_expl_2", "volcanic_plains", "exploratory", 12),
    ("plains_conf_1", "volcanic_plains", "confirmatory", 13),
    ("plains_conf_2", "volcanic_plains", "confirmatory", 14),
    ("plains_conf_3", "volcanic_plains", "confirmatory", 15),
    ("contrast_1", "contrast", "confirmatory", 21),
    ("contrast_2", "contrast", "confirmatory", 22),
)
_PLAINS_AMP, _CONTRAST_AMP = 5.0, 30.0
_REF_DX, _CAND_DX = 60.0, 30.0
_HONEST = [240.0, 300.0]
_CONF_PLAINS = ["plains_conf_1", "plains_conf_2", "plains_conf_3"]
_EXPL_PLAINS = ["plains_expl_1", "plains_expl_2"]
_LENSES = ["core", "extended", "geomorphic", "landform", "texture", "hydro"]


def _panel_scene(contrast_amp=_CONTRAST_AMP, **cfg_over):
    """Synthetic v2 panel -> (grids, spacings, rights, cfg) with known answers."""
    def rf(n, amp, seed):
        return synthetic.rough_field((n, n), amplitude=amp, seed=seed)
    grids = {"X": rf(200, 10.0, 3), "Y": rf(200, 1.0, 4), "Z": rf(160, 60.0, 5)}
    spacings = {u: _CAND_DX for u in grids}
    panel = []
    for rid, cls, status, seed in _PANEL_REFS:
        plains = cls == "volcanic_plains"
        grids[rid] = rf(100, _PLAINS_AMP if plains else contrast_amp, seed)
        spacings[rid] = _REF_DX
        panel.append({"id": rid, "class": cls, "status": status,
                      "expect": {"type": "recommends" if plains else "not_sole", "unit": "X"}})
    rights = {u: "verified_allowed" for u in grids}
    cfg = {"experiment": "matched_footprint_panel_v2_synthetic", "extent_m": 6000.0,
           "honest_supports_m": [150.0] + _HONEST, "diagnostic_supports_m": [90.0],
           "res_factor": 3.0, "resolution_control": True, "adequacy": True,
           "adequacy_support_m": 240.0, "adversarial": True,
           "primary_reference": "plains_expl_1", "min_valid_fraction": 0.5, "seed": 0,
           "candidates": ["X", "Y", "Z"], "panel": panel}
    cfg.update(cfg_over)
    return grids, spacings, rights, cfg


_PANEL_CACHE = {}


def _specific_bundle():
    """Full specific-scenario run (every control on), computed once and shared."""
    if "specific" not in _PANEL_CACHE:
        g, sp, rt, cfg = _panel_scene()
        _PANEL_CACHE["specific"] = matched_real.run_panel_from_grids(g, sp, rt, cfg)
    return _PANEL_CACHE["specific"]


def _nonspecific_bundle():
    """Contrast references X-like, so X wins in every class (H2 must fail). Lean:
    no resolution control / adversarial; a sub-floor adequacy support (150 m) that
    must be substituted."""
    if "nonspecific" not in _PANEL_CACHE:
        g, sp, rt, cfg = _panel_scene(contrast_amp=_PLAINS_AMP, resolution_control=False,
                                      adversarial=False, adequacy_support_m=150.0)
        _PANEL_CACHE["nonspecific"] = matched_real.run_panel_from_grids(g, sp, rt, cfg)
    return _PANEL_CACHE["nonspecific"]


def _fake_honest(recs, verdict="specific", supports=tuple(_HONEST)):
    """Minimal honest-panel dict for rule-level tests. ``recs`` maps a reference id
    to one entry per support: a candidate id (a RECOMMEND_FOLLOW_UP of it) or
    "TIE" / "ERROR". Outcomes come from the real ``evaluate_expectation``."""
    refs = []
    for rid, cls, status, _seed in _PANEL_REFS:
        if rid not in recs:
            continue
        cells = []
        for s, v in zip(supports, recs[rid]):
            if v in ("TIE", "ERROR"):
                cells.append({"support_m": s, "result_state": v, "recommended_unit": None,
                              "pareto_layer1": []})
            else:
                cells.append({"support_m": s, "result_state": "RECOMMEND_FOLLOW_UP",
                              "recommended_unit": v, "pareto_layer1": [v]})
        expect = {"type": "recommends" if cls == "volcanic_plains" else "not_sole", "unit": "X"}
        refs.append({"id": rid, "class": cls, "status": status,
                     "counts_as_confirmation": status == "confirmatory", "cells": cells,
                     "adequacy": None, "expectation": cf.evaluate_expectation(expect, cells)})
    return {"references": refs, "supports_m": list(supports),
            "summary": {"specificity": {"verdict": verdict, "top_unit_by_class": {},
                                        "explanation": "fabricated"}}}


_BASE_RECS = {rid: (["X", "X"] if cls == "volcanic_plains" else ["Z", "Z"])
              for rid, cls, _s, _seed in _PANEL_REFS}


def test_panel_footprint_auto_reduced_and_honest_regime():
    b = _specific_bundle()
    fp = b["footprint"]
    assert fp["reduced"] is True and fp["limiting_unit"] == "Z", fp
    assert fp["requested_m"] == 6000.0 and fp["extent_m"] == 4800.0, fp
    assert b["panel_raw"]["honest"]["extent_m"] == 4800.0
    honest = [c for r in b["panel_raw"]["honest"]["references"] for c in r["cells"]]
    matched = [c for r in b["resolution_control"]["panel_matched"]["honest"]["references"]
               for c in r["cells"]]
    assert len(honest) == len(matched) == len(_PANEL_REFS) * len(_HONEST)
    for c in honest + matched:
        assert c["comparability"]["regime"] in ("honest", "honest+low-power"), c["comparability"]
        assert c["comparability"]["assessment"]["truncated_units"] == []
    assert b["regime_violation"] == {"flag": False, "cells": []}
    # Sub-floor cells are labelled as such -- never "honest".
    for r in b["panel_raw"]["diagnostic"]["references"]:
        for c in r["cells"]:
            assert c["comparability"]["regime"].startswith("below-effective-resolution"), c


def test_panel_sub_floor_honest_support_demoted_with_warning():
    b = _specific_bundle()
    assert b["support_floor"]["floor_m"] == 3.0 * _REF_DX
    s = b["supports"]
    assert s["configured_honest_m"] == [150.0] + _HONEST, s
    assert s["honest_m"] == _HONEST and s["demoted_m"] == [150.0], s
    assert s["diagnostic_m"] == [90.0, 150.0], s
    assert any("150 m" in w and "DEMOTED" in w for w in b["warnings"]), b["warnings"]
    # The demoted support reaches no evidence: only honest supports feed the rules.
    assert b["panel_raw"]["honest"]["supports_m"] == _HONEST
    for fact in b["hypotheses"]["H1"]["evidence"].values():
        assert [p["support_m"] for p in fact["per_support"]] == _HONEST, fact
    for fact in b["hypotheses"]["H2"]["evidence"]["contrast"].values():
        assert [p["support_m"] for p in fact["per_support"]] == _HONEST, fact
    assert [r["support_m"] for r in b["hypotheses"]["H3"]["evidence"]["primary_honest"]] == _HONEST


def test_panel_h1_h2_supported_on_specific_scenario():
    h = _specific_bundle()["hypotheses"]
    assert h["H1"]["verdict"] == "supported", h["H1"]
    assert h["H1"]["counts"]["holds_ids"] == _CONF_PLAINS, h["H1"]["counts"]
    assert "qualifier" not in h["H1"], h["H1"]
    assert h["H2"]["verdict"] == "supported", h["H2"]
    spec = h["H2"]["evidence"]["specificity"]
    assert spec["verdict"] == "specific", spec
    assert spec["top_unit_by_class"] == {"contrast": "Z", "volcanic_plains": "X"}, spec
    for k in ("H1", "H2", "H3", "H4"):
        assert h[k]["rule"].startswith(k + " "), h[k]["rule"]
        assert h[k]["verdict"] in ("supported", "not_supported", "inconclusive", "reported")


def test_panel_h2_not_supported_on_non_specific_scenario():
    b = _nonspecific_bundle()
    h = b["hypotheses"]
    assert h["H2"]["verdict"] == "not_supported", h["H2"]
    assert h["H2"]["evidence"]["specificity"]["verdict"] == "non_specific"
    assert all(f["outcome"] == "fails" for f in h["H2"]["evidence"]["contrast"].values())
    # Per protocol v2 the plains result is then reported as NON-SPECIFIC.
    assert h["H1"]["verdict"] == "supported" and "NON-SPECIFIC" in h["H1"]["qualifier"]
    # No resolution control -> H3 is inconclusive, never silently "supported".
    assert h["H3"]["verdict"] == "inconclusive" and "not run" in h["H3"]["reason"], h["H3"]
    # A sub-floor adequacy support is substituted by the smallest honest support.
    ade = b["adequacy"]
    assert ade["configured_m"] == 150.0 and ade["support_m"] == _HONEST[0], ade
    assert ade["substituted"] is True and any("adequacy" in w for w in b["warnings"])


def test_panel_h3_raw_vs_matched_and_labelled_diagnostic():
    b = _specific_bundle()
    rc = b["resolution_control"]
    assert rc["run"] is True and rc["target_fwhm_m"] == 3.0 * _REF_DX
    rows = [r for r in rc["comparison"] if r["support_class"] == "honest"]
    assert {(r["reference"], r["support_m"]) for r in rows} == {
        (rid, s) for rid, *_ in _PANEL_REFS for s in _HONEST}
    for r in rows:
        assert {"raw_recommendation", "matched_recommendation", "changed"} <= set(r)
    h3 = b["hypotheses"]["H3"]
    assert h3["verdict"] == "supported", h3
    prim = h3["evidence"]["primary_honest"]
    assert [(r["raw_recommendation"], r["matched_recommendation"]) for r in prim] == [("X", "X")] * 2
    assert h3["evidence"]["h1_outcome_raw_vs_matched"] == {
        rid: {"raw": "holds", "matched": "holds"} for rid in _CONF_PLAINS}
    d = h3["diagnostic"]
    assert "never evidence" in d["label"], d
    assert [r["support_m"] for r in d["primary_by_support"]] == [90.0, 150.0], d
    assert all(r["support_class"] == "diagnostic" for r in d["primary_by_support"])
    assert d["v1_500m"] is None and "500 m" in d["note"], d


def test_panel_exploratory_refs_never_counted_toward_h1():
    h1 = _specific_bundle()["hypotheses"]["H1"]
    assert sorted(h1["evidence"]) == _CONF_PLAINS
    assert sorted(h1["exploratory_not_counted"]) == _EXPL_PLAINS
    assert all(v["counted"] is False and v["status"] == "exploratory"
               for v in h1["exploratory_not_counted"].values())
    assert h1["counts"]["confirmatory_refs"] == 3
    # Exploratory references that HOLD cannot rescue confirmatory ones that FAIL.
    recs = dict(_BASE_RECS, plains_conf_1=["Y", "Y"], plains_conf_2=["Y", "Y"])
    assert matched_real._hypothesis_h1(_fake_honest(recs))["verdict"] == "not_supported"


def test_panel_frozen_rules_on_fabricated_outcomes():
    """The literal decision rules, one boundary at a time (mutation guards)."""
    h1, h2, h3 = (matched_real._hypothesis_h1, matched_real._hypothesis_h2,
                  matched_real._hypothesis_h3)
    base = _fake_honest(_BASE_RECS)
    # H1: >= 2 of the 3 hold -> supported ("mixed" is not "holds"); <= 1 -> not.
    two = dict(_BASE_RECS, plains_conf_3=["X", "Y"])
    assert h1(_fake_honest(two))["verdict"] == "supported"
    one = dict(two, plains_conf_2=["TIE", "TIE"])
    assert h1(_fake_honest(one))["verdict"] == "not_supported"
    err = h1(_fake_honest(dict(_BASE_RECS, plains_conf_1=["X", "ERROR"])))
    assert err["verdict"] == "inconclusive" and "ERROR" in err["reason"], err
    short = {k: v for k, v in _BASE_RECS.items() if k != "plains_conf_3"}
    assert h1(_fake_honest(short))["verdict"] == "inconclusive"
    assert h1(None)["verdict"] == "inconclusive"
    # H2: both contrast hold not_sole AND specific -> supported; otherwise not.
    assert h2(base)["verdict"] == "supported"
    assert h2(_fake_honest(dict(_BASE_RECS, contrast_1=["Z", "X"])))["verdict"] == "not_supported"
    assert h2(_fake_honest(_BASE_RECS, verdict="non_specific"))["verdict"] == "not_supported"
    assert h2(_fake_honest(_BASE_RECS, verdict="not_evaluable"))["verdict"] == "inconclusive"
    assert h2(_fake_honest(dict(_BASE_RECS, plains_expl_2=["X", "ERROR"])))["verdict"] == "inconclusive"
    # H3: primary change OR an H1 holds -> fails is NOT supported; holds -> mixed is not a flip.
    p = "plains_expl_1"
    assert h3(base, _fake_honest(_BASE_RECS), True, p, [])["verdict"] == "supported"
    assert h3(base, _fake_honest(dict(_BASE_RECS, plains_expl_1=["X", "Y"])),
              True, p, [])["verdict"] == "not_supported"
    assert h3(base, _fake_honest(dict(_BASE_RECS, plains_conf_2=["Y", "Y"])),
              True, p, [])["verdict"] == "not_supported"
    assert h3(base, _fake_honest(dict(_BASE_RECS, plains_conf_2=["X", "Y"])),
              True, p, [])["verdict"] == "supported"
    assert h3(base, _fake_honest(_BASE_RECS), False, p, [])["verdict"] == "inconclusive"
    assert h3(base, _fake_honest(dict(_BASE_RECS, plains_expl_1=["X", "ERROR"])),
              True, p, [])["verdict"] == "inconclusive"
    # Regime audit: "+low-power" is reported but allowed; any other non-honest regime
    # is a violation; an ERROR cell (no provenance) is listed as unassessed.
    def cell(regime, assessed=True):
        return {"support_m": 240.0, "comparability": {
            "regime": regime, "assessment": {"issues": ["i"]} if assessed else None}}
    violations, low_power, unassessed = matched_real._regime_audit([("raw", {"references": [
        {"id": "r", "cells": [cell("honest"), cell("honest+low-power"),
                              cell("footprint-mismatched+low-power"),
                              cell("unassessed", assessed=False)]}]})])
    assert [v["regime"] for v in violations] == ["footprint-mismatched+low-power"], violations
    assert [c["regime"] for c in low_power] == ["honest+low-power",
                                                "footprint-mismatched+low-power"], low_power
    assert [c["regime"] for c in unassessed] == ["unassessed"], unassessed
    # Regime gate: any honest-regime violation makes H1-H3 inconclusive (rule kept).
    hyp = {"H1": h1(base), "H2": h2(base), "H3": h3(base, base, True, p, []),
           "H4": {"verdict": "reported"}}
    matched_real._apply_regime_gate(hyp, [{"reference": "x", "support_m": 240.0}])
    assert all(hyp[k]["verdict"] == "inconclusive" and hyp[k]["rule_verdict"] == "supported"
               for k in ("H1", "H2", "H3")), hyp


def test_panel_h4_adequacy_reported_per_reference():
    b = _specific_bundle()
    h4 = b["hypotheses"]["H4"]
    assert h4["verdict"] == "reported"
    assert b["adequacy"]["support_m"] == 240.0 and b["adequacy"]["substituted"] is False
    for rid, cls, _s, _seed in _PANEL_REFS:
        e = h4["evidence"][rid]
        assert e["recommended_unit"] == ("X" if cls == "volcanic_plains" else "Z"), e
        assert e["adequacy"] == "adequate", e
    # Established band but no adequate candidate -> the protocol's honest sentence.
    fake = _fake_honest({"plains_conf_1": ["X", "X"], "plains_conf_2": ["X", "X"]})
    fake["references"][0]["adequacy"] = {"support_m": 240.0, "established": True,
                                         "adequate_candidates": [], "any_adequate": False,
                                         "note": "n", "error": None}
    fake["references"][1]["adequacy"] = {"support_m": 240.0, "established": False,
                                         "adequate_candidates": [], "any_adequate": False,
                                         "note": "Absolute morphological adequacy has not "
                                                 "been established.", "error": None}
    ev = matched_real._hypothesis_h4(fake, {"support_m": 240.0})["evidence"]
    assert ev["plains_conf_1"]["adequacy"] == "inadequate"
    assert ev["plains_conf_1"]["statement"] == ("best among these candidates, but outside "
                                                "the reference's own morphological variability.")
    assert ev["plains_conf_2"]["adequacy"] == "not_established"


def test_panel_primary_lens_ablation_and_adversarial():
    pr = _specific_bundle()["primary"]
    assert pr["evaluated"] is True and pr["reference_id"] == "plains_expl_1"
    assert pr["support_m"] == _HONEST[0] and pr["compared_units"] == ["plains_expl_1", "X", "Y", "Z"]
    assert list(pr["lens_ablation"]) == _LENSES
    assert pr["lens_ablation"]["core"]["recommended_unit"] == "X"
    adv = pr["adversarial"]
    assert adv["baseline"]["recommended_unit"] == "X" and adv["seed"] == 0, adv["baseline"]
    assert adv["evidence_status"].startswith("exploratory"), adv
    assert "support_floor_note" in adv          # 0.67 x 240 m < the 180 m floor


def test_panel_deterministic_and_json_serialisable():
    a = _specific_bundle()
    g, sp, rt, cfg = _panel_scene()
    b = matched_real.run_panel_from_grids(g, sp, rt, cfg)
    sa = json.dumps(a, sort_keys=True, allow_nan=False)
    assert sa == json.dumps(b, sort_keys=True, allow_nan=False)
    expected = {"experiment", "protocol", "config", "footprint", "support_floor", "supports",
                "warnings", "adequacy", "panel_raw", "comparability", "regime_violation",
                "resolution_control", "primary", "hypotheses", "limitations", "scope_note",
                "prohibited_claims"}
    assert expected <= set(a), expected - set(a)
    assert a["protocol"]["path"] == "docs/BENCHMARK-PROTOCOL-v2.md"
    sha = a["protocol"]["sha256"]
    assert len(sha) == 64 and all(ch in "0123456789abcdef" for ch in sha), sha
    assert a["config"] == {"path": None, "sha256": None}       # not run from a file
    assert isinstance(a["prohibited_claims"], list) and a["prohibited_claims"]


def test_panel_frozen_texts_match_protocol_document():
    """Rule texts, regime and limitations are copied from the frozen protocol; this
    fails if either the copy or the document drifts."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "docs", "BENCHMARK-PROTOCOL-v2.md"), encoding="utf-8") as fh:
        doc = fh.read()

    def norm(s):
        return " ".join(s.replace("*", "").replace("`", "").split())
    b = _specific_bundle()
    assert len(b["limitations"]) == 5
    texts = (list(b["limitations"]) + [b["hypotheses"][k]["rule"] for k in ("H1", "H2", "H3", "H4")]
             + [b["regime_rule"], b["primary"]["rule"]])
    for text in texts:
        assert norm(text) in norm(doc), text


def test_run_real_panel_end_to_end_monkeypatched():
    """Monkeypatch the v2 rasterio seam and drive run_real_panel end to end: the
    bundle is written, matches the returned one, and the console output is ASCII."""
    g, sp, rt, cfg = _panel_scene(adversarial=False)
    cfg["units"] = [{"id": u} for u in g]
    tmp = tempfile.mkdtemp(prefix="mf_panel_test_")
    seen = []
    original = matched_real.load_panel_grids
    matched_real.load_panel_grids = lambda c: (seen.append(c), (g, sp, rt))[1]
    try:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            bundle = matched_real.run_real_panel(cfg, out=tmp)
        path = os.path.join(tmp, "matched_panel_real.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as fh:
            on_disk = json.load(fh)
        assert on_disk == json.loads(json.dumps(bundle))
        assert on_disk["hypotheses"]["H1"]["verdict"] == "supported"
        assert on_disk["primary"]["adversarial"] is None
        assert seen == [cfg]
        text = buf.getvalue()
        assert text.isascii() and "H1 confirmation" in text and "LIMITATIONS" in text, text
    finally:
        matched_real.load_panel_grids = original
        shutil.rmtree(tmp, ignore_errors=True)


def _load_script():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    spec = importlib.util.spec_from_file_location(
        "run_matched_benchmark_under_test",
        os.path.join(root, "scripts", "run_matched_benchmark.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_dispatch_panel_to_v2_else_v1_and_honest_block():
    script = _load_script()
    calls = []
    original = (matched_real.run_real_panel, matched_real.run_real_matched)
    matched_real.run_real_panel = lambda c, out=None: (calls.append(("v2", c, out)), "v2")[1]
    matched_real.run_real_matched = lambda c, out=None: (calls.append(("v1", c, out)), "v1")[1]

    def blocked(c, out=None):
        raise ImportError("rasterio missing")
    try:
        assert script.dispatch({"panel": [], "units": []}, "o2", config_path="c.yml") == "v2"
        assert calls[-1][0] == "v2" and calls[-1][2] == "o2"
        assert calls[-1][1]["config_path"] == "c.yml"
        assert script.dispatch({"reference_id": "r", "units": []}, "o1") == "v1"
        assert calls[-1][0] == "v1" and "config_path" not in calls[-1][1]
        # No rasterio -> honest blocked message + exit 2, worded for the right protocol.
        for cfg, runner, needle in (
                ({"panel": [{"id": "r"}]}, "run_real_panel", "BENCHMARK-PROTOCOL-v2.md"),
                ({"reference_id": "r"}, "run_real_matched", "matched_footprint.example.yml")):
            setattr(matched_real, runner, blocked)
            script._load_config = lambda path, cfg=cfg: cfg
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = script.main(["--config", "x.yml", "--out", "unused"])
            assert code == 2 and "BLOCKED" in buf.getvalue() and needle in buf.getvalue()
    finally:
        matched_real.run_real_panel, matched_real.run_real_matched = original


def test_panel_run_leaves_gated_study_hash_unchanged():
    """Gated: the default study package hash is 64 lowercase hex and identical
    before and after a v2 panel run (no shared state is perturbed)."""
    h1 = study.run_study()["package_hash"]
    g, sp, rt, cfg = _panel_scene(resolution_control=False, adversarial=False,
                                  adequacy=False, diagnostic_supports_m=[])
    with contextlib.redirect_stdout(io.StringIO()):
        matched_real.run_panel_from_grids(g, sp, rt, cfg)
    h2 = study.run_study()["package_hash"]
    assert len(h1) == 64 and all(c in "0123456789abcdef" for c in h1), h1
    assert h1 == h2
