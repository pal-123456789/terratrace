"""Planetary / terrestrial-analog region-library presets."""
from terratrace import regions, preflight

_BODIES = ("mars", "earth", "moon", "mercury", "ceres")


def test_all_regions_nonempty_and_every_preset_is_wellformed():
    ids = regions.all_regions()
    assert ids                                         # non-empty
    assert ids == sorted(ids)                          # all_regions() is sorted
    for rid in ids:
        r = regions.get(rid)
        assert r["id"] == rid
        assert r["body"] in _BODIES
        bbox = r["bbox"]
        assert isinstance(bbox, (list, tuple)) and len(bbox) == 4
        assert all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in bbox)
        # Every curated preset must pass the engine's own bbox gate for its body.
        assert preflight.validate_bbox(bbox, r["body"]) == []


def test_by_body_includes_expected_sites():
    mars_ids = {r["id"] for r in regions.by_body("mars")}
    earth_ids = {r["id"] for r in regions.by_body("earth")}
    assert "jezero_crater" in mars_ids
    assert "hawaii_mauna_loa" in earth_ids
    # by_body is body-scoped: an earth site never leaks into the mars list.
    assert "hawaii_mauna_loa" not in mars_ids


def test_to_aoi_unit_shape_and_validates():
    u = regions.to_aoi_unit("jezero_crater", is_reference=True)
    assert u["is_reference"] is True
    assert u["body"] == "mars"
    assert u["rights_status"] == "verified_allowed"
    assert isinstance(u["suggested_source"], str) and u["suggested_source"]
    assert isinstance(u["bbox"], (list, tuple)) and len(u["bbox"]) == 4
    assert u["path"] == "data/mars/jezero_crater.tif"      # default path convention
    assert u["access_status"] == "unknown"
    # The emitted unit is itself a well-formed AOI for preflight.
    assert preflight.validate_bbox(u["bbox"], u["body"]) == []


def test_to_aoi_unit_extra_knobs_flow_through_but_not_control_knob():
    u = regions.to_aoi_unit("craters_of_the_moon", demtype="COP30",
                            native_posting_m=30.0, target_support_m=1000.0)
    assert u["demtype"] == "COP30"
    assert u["native_posting_m"] == 30.0
    assert u["is_reference"] is False
    assert "target_support_m" not in u                     # control knob, not emitted
    assert isinstance(u["suggested_source"], str)


def test_to_aoi_units_marks_single_reference():
    units = regions.to_aoi_units(["jezero_crater", "hawaii_mauna_loa"],
                                 reference_id="jezero_crater")
    assert len(units) == 2
    refs = [u for u in units if u["is_reference"]]
    assert len(refs) == 1 and refs[0]["id"] == "jezero_crater"


def test_get_unknown_raises():
    try:
        regions.get("no_such_place")
        raised = False
    except KeyError:
        raised = True
    assert raised


def test_validate_is_clean_for_shipped_presets():
    # Every hand-authored preset is internally consistent and bbox-valid.
    assert regions.validate() == []
