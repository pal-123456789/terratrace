"""Real-study entry-point wiring, exercised WITHOUT rasterio or the network.

`run_real_study` is the function users actually call on real DEMs, but its raster
load needs rasterio (absent in CI). The load step is isolated in
`study.load_real_units`; here we substitute synthetic arrays for it and prove the
REST of the real path works end to end: reference detection, per-unit vertical-
accuracy resolution (explicit override + catalog lookup by demtype), the opt-in
feature-uncertainty + hillshade-preview blocks, and the geomorphic decision lens.
This guards the real path against regressions that unit tests on compare_units
alone would miss.
"""
import numpy as np

from terratrace import study, synthetic


def _fake_arrays(ids):
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    return {
        ids[0]: base + synthetic.rough_field((64, 64), 0.6, seed=1),
        ids[1]: base + synthetic.rough_field((64, 64), 0.7, seed=2),
        ids[2]: base + synthetic.rough_field((64, 64), 3.0, seed=3),
    }


def _run_with_fake_load(units, **kwargs):
    ids = [u["id"] for u in units]
    raw = _fake_arrays(ids)
    rights = {i: "verified_allowed" for i in ids}
    native = {i: 10.0 for i in ids}
    ref_ids = [u["id"] for u in units if u.get("is_reference")]
    original = study.load_real_units
    study.load_real_units = lambda u, t, r: (raw, rights, native, ref_ids)
    try:
        return study.run_real_study(units, target_support_m=10.0, **kwargs)
    finally:
        study.load_real_units = original


def test_run_real_study_resolves_uncertainty_previews_and_lens():
    units = [
        {"id": "mars_ref", "body": "mars", "is_reference": True, "path": "ref.tif",
         "vertical_accuracy_m": 3.0},                       # explicit override
        {"id": "earth_a", "body": "earth", "demtype": "COP30", "path": "a.tif"},
        {"id": "earth_b", "body": "earth", "demtype": "COP30", "path": "b.tif"},
    ]
    pkg = _run_with_fake_load(units, previews=True, decision_metrics="geomorphic")

    assert pkg["result_state"] in study.decision.STATES
    assert pkg["profile"]["decision_metrics"] == "geomorphic"
    # per-unit vertical accuracy: explicit override for the reference, catalog
    # COP30 (4.0 m) resolved by demtype for the Earth units.
    fu = pkg["feature_uncertainty"]
    assert abs(fu["mars_ref"]["sigma_z"] - 3.0) < 1e-9
    assert abs(fu["earth_a"]["sigma_z"] - 4.0) < 1e-9
    assert abs(fu["earth_b"]["sigma_z"] - 4.0) < 1e-9
    assert all(r["relief_sigma_m"] > 0 for r in fu.values())
    # one self-contained hillshade preview per unit.
    assert set(pkg["previews"]) == {"mars_ref", "earth_a", "earth_b"}
    assert all(v.startswith("data:image/png;base64,") for v in pkg["previews"].values())


def test_run_real_study_defaults_are_clean():
    # With no previews and no resolvable vertical accuracy, the optional blocks
    # are simply absent (nothing crashes, nothing half-populated).
    units = [
        {"id": "mars_ref", "body": "mars", "is_reference": True, "path": "ref.tif"},
        {"id": "earth_a", "body": "earth", "path": "a.tif"},       # no demtype -> no vacc
        {"id": "earth_b", "body": "earth", "path": "b.tif"},
    ]
    pkg = _run_with_fake_load(units)
    assert pkg["result_state"] in study.decision.STATES
    assert "previews" not in pkg
    assert "feature_uncertainty" not in pkg       # none resolvable -> block omitted


def test_run_real_study_requires_a_reference():
    units = [{"id": "earth_a", "body": "earth", "path": "a.tif"},
             {"id": "earth_b", "body": "earth", "path": "b.tif"},
             {"id": "earth_c", "body": "earth", "path": "c.tif"}]
    raised = False
    try:
        _run_with_fake_load(units)
    except ValueError:
        raised = True
    assert raised                                 # no is_reference -> clear error
