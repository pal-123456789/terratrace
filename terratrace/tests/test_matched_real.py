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
"""
import json
import os
import shutil
import tempfile

import numpy as np

from terratrace import matched_real, synthetic, study, reproject

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
