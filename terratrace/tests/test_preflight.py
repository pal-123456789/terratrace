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
        "reference": {"id": "mars_ref", "body": "mars",
                      "bbox": [120.0, -5.0, 130.0, 5.0], "native_posting_m": 463.0},
        "earth_units": [
            {"id": "earth_a", "body": "earth", "demtype": "COP30",
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

