"""Source-catalog fixtures."""
from terratrace import catalog


def test_registry_is_valid_and_complete():
    assert catalog.validate() == []            # every entry has all required fields
    assert len(catalog.all_ids()) >= 5


def test_get_and_by_body():
    assert catalog.get("earth_cop30")["key_required"] is True
    assert catalog.get("mars_mola_megdr")["body"] == "mars"
    mars = {s["id"] for s in catalog.by_body("mars")}
    assert "mars_mola_megdr" in mars and "earth_cop30" not in mars


def test_3dep_is_public_domain_and_keyless_path_exists():
    assert "public domain" in catalog.get("earth_usgs1m")["license"].lower()
    assert catalog.get("earth_usgs1m")["key_required"] is False   # ImageServer/TNM path
    assert catalog.get("earth_usgs10m")["access"]["datasetName"] == "USGS10m"


def test_unknown_source_raises():
    try:
        catalog.get("nope")
        raised = False
    except KeyError:
        raised = True
    assert raised


def test_validate_catches_injected_defects():
    # validate() must flag a bad entry, not just pass the hand-authored ones.
    # Inject several distinct defects, then restore the registry.
    bad = {
        "id": "mismatched_id",                       # != its key -> id field mismatch
        "body": "venus",                             # not mars/earth
        "provider": "x", "product": "y",
        "native_resolution_m": -1.0,                 # not positive
        "access": {"endpoint": "z"},                 # access.method missing
        "crs": "c", "vertical_datum": "v",
        "key_required": "yes",                       # not bool
        # "license" and "citation" intentionally omitted -> missing field
    }
    catalog.SOURCES["__defect__"] = bad
    try:
        problems = catalog.validate()
    finally:
        del catalog.SOURCES["__defect__"]
    msgs = [p[1] for p in problems if p[0] == "__defect__"]
    assert any("id field mismatch" in m for m in msgs)
    assert any("body not in mars/earth" in m for m in msgs)
    assert any("native_resolution_m not positive" in m for m in msgs)
    assert any("access.method missing" in m for m in msgs)
    assert any("key_required not bool" in m for m in msgs)
    assert any("missing field license" in m for m in msgs)
    assert any("missing field citation" in m for m in msgs)
    # And the real registry is clean again after restore.
    assert catalog.validate() == []


def test_all_bodies_are_known_and_resolutions_positive():
    for sid in catalog.all_ids():
        s = catalog.get(sid)
        assert s["body"] in ("mars", "earth")
        assert s["native_resolution_m"] > 0
    assert {s["id"] for s in catalog.by_body("earth")} >= {"earth_cop30", "earth_usgs10m"}


# --- coverage + source selection -------------------------------------------
_CRATERS = (-113.60, 43.30, -113.30, 43.60)   # Idaho, inside US 3DEP CONUS box
_ANDES = (-78.60, -0.20, -78.30, 0.10)        # Ecuador, outside any US box
_MARS = (120.0, -5.0, 130.0, 5.0)


def test_source_covers_global_and_regional():
    # Mars global product covers any Mars bbox.
    assert catalog.source_covers("mars_mola_usgs_463m", _MARS, "mars")["covered"] is True
    # Copernicus is global land -> covers both US and non-US land bboxes.
    assert catalog.source_covers("earth_cop30", _CRATERS, "earth")["covered"] is True
    assert catalog.source_covers("earth_cop30", _ANDES, "earth")["covered"] is True
    # 3DEP 10 m covers a CONUS bbox but NOT the Andes.
    assert catalog.source_covers("earth_usgs10m", _CRATERS, "earth")["covered"] is True
    assert catalog.source_covers("earth_usgs10m", _ANDES, "earth")["covered"] is False


def test_source_covers_flags_body_mismatch_and_partial():
    bad = catalog.source_covers("earth_cop30", _MARS, "mars")
    assert bad["covered"] is False and "body mismatch" in bad["reason"]
    # 1 m lidar footprint is advertised but not continuous -> complete False.
    partial = catalog.source_covers("earth_usgs1m", _CRATERS, "earth")
    assert partial["covered"] is True and partial["complete"] is False


def test_recommend_source_picks_closest_to_target_support():
    # In the US at ~10 m target, the 10 m seamless product is the right call
    # (coarsest native that still reaches the target -> least download).
    r = catalog.recommend_source(_CRATERS, "earth", target_support_m=10.0)
    assert r["source_id"] == "earth_usgs10m"
    # At a 1000 m common support, the global 30 m product is enough and cheapest.
    r2 = catalog.recommend_source(_CRATERS, "earth", target_support_m=1000.0)
    assert r2["source_id"] == "earth_cop30"
    # A partial source we did NOT choose must not leak a coverage warning.
    assert not any("earth_usgs1m" in w for w in r2["warnings"])


def test_recommend_source_warns_only_about_chosen_partial_source():
    # When the only keyless option is the partial 1 m lidar, choosing it DOES warn.
    r = catalog.recommend_source(_CRATERS, "earth", target_support_m=30.0, require_keyless=True)
    assert r["source_id"] == "earth_usgs1m"
    assert any("earth_usgs1m" in w and "verify" in w.lower() for w in r["warnings"])


def test_recommend_source_non_us_falls_back_to_global():
    r = catalog.recommend_source(_ANDES, "earth", target_support_m=90.0)
    assert r["source_id"] == "earth_cop30"
    assert r["candidates"] == ["earth_cop30"]            # US products don't cover it


def test_recommend_source_warns_when_target_finer_than_any_source():
    r = catalog.recommend_source(_ANDES, "earth", target_support_m=5.0)
    assert r["source_id"] == "earth_cop30"               # only covered source
    assert any("finer than any covered" in w for w in r["warnings"])


def test_recommend_source_require_keyless_excludes_api_sources():
    r = catalog.recommend_source(_CRATERS, "earth", target_support_m=30.0, require_keyless=True)
    assert r["source_id"] == "earth_usgs1m"              # only keyless US product
    assert catalog.get(r["source_id"])["key_required"] is False


def test_recommend_source_mars_and_empty():
    r = catalog.recommend_source(_MARS, "mars", target_support_m=1000.0)
    assert r["source_id"] in ("mars_mola_megdr", "mars_mola_usgs_463m")
    # Genuine "no covered source": a non-US land bbox with keyless required leaves
    # nothing (COP30 needs a key; US products don't reach the Andes).
    empty = catalog.recommend_source(_ANDES, "earth", target_support_m=30.0, require_keyless=True)
    assert empty["source_id"] is None and empty["candidates"] == []


def test_coverage_defect_is_flagged_by_validate():
    cov_bad = dict(catalog.get("earth_cop30"))
    cov_bad = {**cov_bad, "coverage": {"kind": "bogus", "valid_resolution_range_m": [10, 1]}}
    catalog.SOURCES["__covbad__"] = {**cov_bad, "id": "__covbad__"}
    try:
        problems = catalog.validate()
    finally:
        del catalog.SOURCES["__covbad__"]
    msgs = [p[1] for p in problems if p[0] == "__covbad__"]
    assert any("coverage.kind unknown" in m for m in msgs)
    assert any("valid_resolution_range_m invalid" in m for m in msgs)
