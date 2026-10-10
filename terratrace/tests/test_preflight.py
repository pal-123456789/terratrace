"""Preflight AOI/bbox/coverage validation fixtures (dependency-free)."""
from terratrace import preflight


# Geometry fixtures reused across tests.
_CRATERS = (-113.60, 43.30, -113.30, 43.60)   # Idaho, inside US 3DEP CONUS box
_ANDES = (-78.60, -0.20, -78.30, 0.10)        # Ecuador, outside any US box
_ANDES_HUGE = (-80.0, -10.0, -70.0, 0.0)      # 10x10 deg non-US -> oversized
_MARS = (120.0, -5.0, 130.0, 5.0)             # equatorial Mars window (0..360 lon)


# --- validate_bbox ----------------------------------------------------------
def test_validate_bbox_accepts_good_box():
    assert preflight.validate_bbox((0.0, 0.0, 1.0, 1.0), "earth") == []
    assert preflight.validate_bbox(_CRATERS, "earth") == []


def test_validate_bbox_rejects_bad_ordering():
    assert preflight.validate_bbox((5.0, 0.0, 1.0, 1.0), "earth")   # west >= east
    assert preflight.validate_bbox((0.0, 5.0, 1.0, 1.0), "earth")   # south >= north
    assert preflight.validate_bbox((1.0, 0.0, 1.0, 1.0), "earth")   # zero-span (degenerate)


def test_validate_bbox_rejects_latitude_out_of_range():
    probs = preflight.validate_bbox((0.0, -5.0, 1.0, 95.0), "earth")
    assert any("latitude" in m for m in probs)


def test_validate_bbox_rejects_bad_body():
    assert any("body" in m for m in preflight.validate_bbox((0.0, 0.0, 1.0, 1.0), "venus"))


def test_validate_bbox_mars_accepts_0_360_and_rejects_400():
    # MOLA may be served in 0..360, so a 120..130 E box is valid on Mars...
    assert preflight.validate_bbox(_MARS, "mars") == []
    # ...but 400 is off the planet in any longitude convention.
    probs = preflight.validate_bbox((120.0, -5.0, 400.0, 5.0), "mars")
    assert any("longitude" in m and "400" in m for m in probs)


def test_validate_bbox_earth_rejects_lon_over_180():
    # The same 200 E box Mars tolerates in 0..360 is invalid on Earth.
    assert any("longitude" in m
               for m in preflight.validate_bbox((120.0, -5.0, 200.0, 5.0), "earth"))


# --- area / pixels / download ----------------------------------------------
def test_bbox_area_km2_equatorial_sanity_and_body_scaling():
    earth = preflight.bbox_area_km2((0.0, 0.0, 1.0, 1.0), "earth")
    assert 10000.0 < earth < 14000.0         # ~111 km x 111 km near the equator
    mars = preflight.bbox_area_km2((0.0, 0.0, 1.0, 1.0), "mars")
    assert mars < earth                      # smaller planet -> smaller box


def test_moon_body_accepted_and_scaled_smaller_than_mars():
    # Moon is a supported body; a 0..360 lunar bbox is valid and its area scales
    # with the (smaller) lunar radius.
    assert preflight.validate_bbox((120.0, -5.0, 130.0, 5.0), "moon") == []
    moon = preflight.bbox_area_km2((0.0, 0.0, 1.0, 1.0), "moon")
    mars = preflight.bbox_area_km2((0.0, 0.0, 1.0, 1.0), "mars")
    assert 0.0 < moon < mars                 # Moon radius < Mars radius
    # A Moon AOI resolves to the LOLA product via preflight's source selection.
    unit = {"id": "moon_aoi", "body": "moon", "bbox": (120.0, -5.0, 130.0, 5.0),
            "native_posting_m": 118.0}
    res = preflight.preflight_unit(unit, "moon", target_support_m=2000.0)
    assert res["recommended_source"]["source_id"] == "moon_lola_ldem"


def test_estimate_pixels_and_download_are_monotonic():
    small = preflight.estimate_pixels(_CRATERS, 30.0, "earth")
    big = preflight.estimate_pixels(_ANDES_HUGE, 30.0, "earth")
    assert big > small                       # bigger bbox -> more pixels
    coarse = preflight.estimate_pixels(_CRATERS, 30.0, "earth")
    fine = preflight.estimate_pixels(_CRATERS, 10.0, "earth")
    assert fine > coarse                     # finer resolution -> more pixels
    assert preflight.estimate_download_mb(2000) > preflight.estimate_download_mb(1000)


# --- preflight_unit ---------------------------------------------------------
def test_preflight_unit_non_us_bbox_does_not_pick_us_product():
    # An AOI the user *wanted* at USGS10m but that sits outside the US: the
    # catalog must fall back to global COP30, never a US-only product, and a
    # 10x10 deg request must trip an (approximate) size warning. No
    # native_posting_m is set, so resolution falls back to the recommendation.
    unit = {"id": "andes_big", "body": "earth", "dataset": "USGS10m", "bbox": _ANDES_HUGE}
    res = preflight.preflight_unit(unit, "earth", target_support_m=1000.0)
    rec = res["recommended_source"]
    assert rec is not None and rec["source_id"] == "earth_cop30"
    assert "earth_usgs10m" not in rec["candidates"]   # no US source covers the Andes
    assert "earth_usgs1m" not in rec["candidates"]
    assert any("exceeds" in w for w in res["warnings"])   # oversized -> warning


def test_preflight_unit_invalid_bbox_bails_early():
    unit = {"id": "bad", "body": "earth", "bbox": (5.0, 0.0, 1.0, 1.0)}   # west > east
    res = preflight.preflight_unit(unit, "earth", target_support_m=1000.0)
    assert res["ok"] is False
    assert res["problems"] and res["estimates"] == {}
    assert res["recommended_source"] is None


def test_preflight_unit_valid_small_box_is_ok():
    unit = {"id": "craters", "body": "earth", "demtype": "COP30",
            "bbox": _CRATERS, "native_posting_m": 30.0}
    res = preflight.preflight_unit(unit, "earth", target_support_m=1000.0)
    assert res["ok"] is True
    assert res["estimates"]["pixels"] > 0
    assert res["recommended_source"]["source_id"] == "earth_cop30"
# --- preflight_config -------------------------------------------------------
def _good_cfg():
    # A valid Mars reference + one valid COP30 earth unit (all inline, no I/O).
    return {
        "target_support_m": 1000.0,
        "reference": {"id": "mars_ref", "body": "mars", "path": "data/mars/ref.tif",
                      "bbox": [120.0, -5.0, 130.0, 5.0], "native_posting_m": 463.0},
        "earth_units": [
            {"id": "earth_a", "body": "earth", "demtype": "COP30",
             "path": "data/earth/a.tif",
             "bbox": [-113.60, 43.30, -113.30, 43.60], "native_posting_m": 30.0},
        ],
    }


def test_preflight_config_all_valid_is_ok():
    r = preflight.preflight_config(_good_cfg())
    assert r["ok"] is True
    assert r["problems"] == []
    assert set(r["units"]) == {"mars_ref", "earth_a"}
    assert r["target_support_m"] == 1000.0


def test_preflight_config_broken_bbox_fails_with_flat_problem():
    cfg = _good_cfg()
    # Flip west/east on the earth unit so west > east -> that unit is not ok.
    cfg["earth_units"][0]["id"] = "earth_bad"
    cfg["earth_units"][0]["bbox"] = [-113.30, 43.30, -113.60, 43.60]
    r = preflight.preflight_config(cfg)
    assert r["ok"] is False
    assert any(p.startswith("earth_bad:") and "west" in p for p in r["problems"])


# --- validate_config (structural/schema gate) -------------------------------
def test_validate_config_clean_cfg_is_empty_and_ok():
    assert preflight.validate_config(_good_cfg()) == []
    assert preflight.preflight_config(_good_cfg())["ok"] is True


def test_validate_config_duplicate_ids_flagged():
    cfg = _good_cfg()
    # Second earth unit reuses "earth_a" but with a distinct path.
    cfg["earth_units"].append(
        {"id": "earth_a", "body": "earth", "demtype": "COP30",
         "path": "data/earth/a2.tif",
         "bbox": [-113.60, 43.30, -113.30, 43.60], "native_posting_m": 30.0})
    probs = preflight.validate_config(cfg)
    assert any("earth_a" in p and "duplicate" in p.lower() for p in probs)
    r = preflight.preflight_config(cfg)
    assert r["ok"] is False
    assert any(p.startswith("config:") and "earth_a" in p for p in r["problems"])


def test_validate_config_duplicate_paths_flagged():
    cfg = _good_cfg()
    # Distinct id, but the same output path as earth_a.
    cfg["earth_units"].append(
        {"id": "earth_b", "body": "earth", "demtype": "COP30",
         "path": "data/earth/a.tif",
         "bbox": [-113.60, 43.30, -113.30, 43.60], "native_posting_m": 30.0})
    probs = preflight.validate_config(cfg)
    assert any("data/earth/a.tif" in p and "duplicate" in p.lower() for p in probs)


def test_validate_config_demtype_and_dataset_conflict_flagged():
    cfg = _good_cfg()
    cfg["earth_units"][0]["dataset"] = "USGS10m"   # already carries demtype COP30
    probs = preflight.validate_config(cfg)
    assert any("demtype" in p and "dataset" in p for p in probs)


# PLACEHOLDER_MORE_TESTS


def test_validate_config_missing_path_flagged_with_identifier():
    cfg = _good_cfg()
    del cfg["earth_units"][0]["path"]
    probs = preflight.validate_config(cfg)
    assert any("path" in p and ("earth_a" in p or "earth_units[0]" in p) for p in probs)


def test_validate_config_missing_id_and_bbox_flagged():
    cfg = _good_cfg()
    del cfg["earth_units"][0]["id"]
    del cfg["earth_units"][0]["bbox"]
    probs = preflight.validate_config(cfg)
    assert any("'id'" in p and "earth_units[0]" in p for p in probs)
    assert any("'bbox'" in p and "earth_units[0]" in p for p in probs)


def test_validate_config_earth_units_not_a_list_flagged_no_crash():
    cfg = _good_cfg()
    cfg["earth_units"] = {"earth_a": {"body": "earth"}}   # a dict, not a list
    probs = preflight.validate_config(cfg)
    assert any("earth_units" in p and "list" in p for p in probs)
    # preflight_config must degrade on the non-list, not raise.
    r = preflight.preflight_config(cfg)
    assert r["ok"] is False
    assert any(p.startswith("config:") and "earth_units" in p for p in r["problems"])


def test_validate_config_cfg_not_a_dict_no_crash():
    assert preflight.validate_config(None) == ["cfg must be a dict"]
    assert any("dict" in p for p in preflight.validate_config([1, 2, 3]))
    # preflight_config must degrade gracefully, not raise.
    r = preflight.preflight_config(None)
    assert r["ok"] is False
    assert r["units"] == {}
    assert r["problems"] == ["config: cfg must be a dict"]
    assert r["target_support_m"] == 1000.0


def test_validate_config_out_of_range_bbox_surfaces():
    cfg = _good_cfg()
    cfg["earth_units"][0]["bbox"] = [-113.30, 43.30, -113.60, 43.60]   # west > east
    probs = preflight.validate_config(cfg)
    assert any("west" in p and ("earth_a" in p or "earth_units[0]" in p) for p in probs)


def test_validate_config_bad_scalars_flagged():
    cfg = _good_cfg()
    cfg["target_support_m"] = -5.0
    cfg["min_valid_fraction"] = 1.5
    probs = preflight.validate_config(cfg)
    assert any("target_support_m" in p for p in probs)
    assert any("min_valid_fraction" in p for p in probs)
    # A bool must not pass as a valid number (bool is an int subclass).
    cfg2 = _good_cfg()
    cfg2["target_support_m"] = True
    assert any("target_support_m" in p for p in preflight.validate_config(cfg2))

