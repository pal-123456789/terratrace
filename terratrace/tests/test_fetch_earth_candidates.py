"""Offline tests for ``scripts/fetch_earth_candidates.py``.

The fetch path is what makes the v3 benchmark reproducible from a clean clone, so
it is worth testing properly -- but the tests must stay dependency-free (CI has
NumPy only). Every network/rasterio call is monkeypatched, and configs are passed
as plain dicts and JSON (never YAML, which CI does not install).

House style: plain ``def test_*()``, assert-based, no pytest, no unittest.
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

_HERE = pathlib.Path(os.path.dirname(os.path.abspath(__file__)))
_ROOT = _HERE.parent
sys.path.insert(0, str(_ROOT))

from terratrace import cop30_cog, reproject


def _load_script():
    """Import scripts/fetch_earth_candidates.py (it is not a package)."""
    path = _ROOT / "scripts" / "fetch_earth_candidates.py"
    spec = importlib.util.spec_from_file_location("fetch_earth_candidates", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


fetcher = _load_script()


# --------------------------------------------------------------------------- #
# Geometry                                                                     #
# --------------------------------------------------------------------------- #
def test_center_bbox_is_symmetric_about_the_centre():
    bbox = fetcher._center_bbox(76.0, 20.0, 60000.0)
    west, south, east, north = bbox
    assert abs((west + east) / 2.0 - 76.0) < 1e-9
    assert abs((south + north) / 2.0 - 20.0) < 1e-9


def test_center_bbox_side_is_the_requested_extent_in_metres():
    r = reproject.body_radius_m("earth")
    for lat in (0.0, 20.0, -30.3, 65.23):
        w, s, e, n = fetcher._center_bbox(10.0, lat, 60000.0)
        import math
        # Latitude side is exact on a sphere; longitude is scaled by cos(lat).
        assert abs(math.radians(n - s) * r - 60000.0) < 1.0
        assert abs(math.radians(e - w) * r * math.cos(math.radians(lat)) - 60000.0) < 1.0


def test_center_bbox_uses_the_body_radius_not_a_hard_coded_earth_one():
    # Mars is smaller, so the same angular window must be requested in degrees
    # that differ from Earth's -- i.e. the body argument is actually honoured.
    e = fetcher._center_bbox(10.0, 0.0, 60000.0, body="earth")
    m = fetcher._center_bbox(10.0, 0.0, 60000.0, body="mars")
    assert abs((e[3] - e[1]) - (m[3] - m[1])) > 1e-6


def test_body_radius_is_shared_with_the_engine():
    assert fetcher.reproject.body_radius_m("earth") == reproject.body_radius_m("earth")


# --------------------------------------------------------------------------- #
# Config loading (JSON only -- CI has no PyYAML)                               #
# --------------------------------------------------------------------------- #
def test_load_config_reads_json_without_yaml():
    with tempfile.TemporaryDirectory() as d:
        p = os.path.join(d, "cfg.json")
        with open(p, "w") as f:
            json.dump({"units": [{"id": "x"}]}, f)
        assert fetcher._load_config(p) == {"units": [{"id": "x"}]}


# --------------------------------------------------------------------------- #
# fetch_units                                                                  #
# --------------------------------------------------------------------------- #
def _cfg(units):
    return {"units": units}


def test_fetch_units_skips_mars_units_and_fetches_only_earth():
    calls = []

    def fake_fetch(bbox, out_path, min_coverage=0.99):
        calls.append((bbox, out_path))
        open(out_path, "wb").write(b"x")
        return out_path

    real = cop30_cog.fetch_cop30_cog
    cop30_cog.fetch_cop30_cog = fake_fetch
    try:
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg([
                {"id": "mars_arcadia", "body": "mars", "path": "data/mars/mola.tif",
                 "center_lon_e": 188.15, "center_lat": 49.02},
                {"id": "earth_nullarbor", "body": "earth",
                 "path": "data/earth/nullarbor_cop30.tif",
                 "center_lon_e": 129.0, "center_lat": -30.3},
            ])
            out = fetcher.fetch_units(cfg, d, source="cog")
    finally:
        cop30_cog.fetch_cop30_cog = real
    ids = [r[0] for r in out]
    assert ids == ["earth_nullarbor"], f"mars units must never be fetched: {ids}"
    assert len(calls) == 1


def test_fetch_units_uses_a_60km_default_extent_and_passes_the_centre_bbox():
    seen = {}

    def fake_fetch(bbox, out_path, min_coverage=0.99):
        seen["bbox"] = bbox
        open(out_path, "wb").write(b"x")
        return out_path

    real = cop30_cog.fetch_cop30_cog
    cop30_cog.fetch_cop30_cog = fake_fetch
    try:
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg([{"id": "e", "body": "earth", "path": "data/earth/e.tif",
                         "center_lon_e": 10.0, "center_lat": 0.0}])
            fetcher.fetch_units(cfg, d, source="cog")
    finally:
        cop30_cog.fetch_cop30_cog = real
    w, s, e, n = seen["bbox"]
    assert abs((e - w) * 111319.5 - 60000.0) < 200.0
    assert abs((n - s) * 111319.5 - 60000.0) < 200.0


def test_fetch_units_prefers_an_explicit_bbox_over_the_centre():
    seen = {}

    def fake_fetch(bbox, out_path, min_coverage=0.99):
        seen["bbox"] = bbox
        open(out_path, "wb").write(b"x")
        return out_path

    real = cop30_cog.fetch_cop30_cog
    cop30_cog.fetch_cop30_cog = fake_fetch
    try:
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg([{"id": "e", "body": "earth", "path": "data/earth/e.tif",
                         "bbox": [1.0, 2.0, 3.0, 4.0],
                         "center_lon_e": 10.0, "center_lat": 0.0}])
            fetcher.fetch_units(cfg, d, source="cog")
    finally:
        cop30_cog.fetch_cop30_cog = real
    assert seen["bbox"] == (1.0, 2.0, 3.0, 4.0)


def test_fetch_units_is_idempotent_and_reports_cached():
    calls = []

    def fake_fetch(bbox, out_path, min_coverage=0.99):
        calls.append(out_path)
        open(out_path, "wb").write(b"x")
        return out_path

    real = cop30_cog.fetch_cop30_cog
    cop30_cog.fetch_cop30_cog = fake_fetch
    try:
        with tempfile.TemporaryDirectory() as d:
            cfg = _cfg([{"id": "e", "body": "earth", "path": "data/earth/e.tif",
                         "center_lon_e": 10.0, "center_lat": 0.0}])
            first = fetcher.fetch_units(cfg, d, source="cog")
            second = fetcher.fetch_units(cfg, d, source="cog")
            forced = fetcher.fetch_units(cfg, d, source="cog", force=True)
    finally:
        cop30_cog.fetch_cop30_cog = real
    assert first[0][2].startswith("fetched")
    assert second[0][2] == "cached"
    assert forced[0][2].startswith("fetched")
    assert len(calls) == 2, "a cached tile must not be re-fetched unless forced"


def test_fetch_units_refuses_the_keyed_source_without_an_api_key():
    with tempfile.TemporaryDirectory() as d:
        cfg = _cfg([{"id": "e", "body": "earth", "path": "data/earth/e.tif",
                     "center_lon_e": 10.0, "center_lat": 0.0}])
        try:
            fetcher.fetch_units(cfg, d, source="opentopo", api_key=None)
        except SystemExit as exc:
            assert "OPENTOPO_API_KEY" in str(exc)
        else:
            raise AssertionError("expected SystemExit without an API key")


def test_main_parses_arguments_without_touching_the_network():
    with tempfile.TemporaryDirectory() as d:
        cfg = os.path.join(d, "cfg.json")
        with open(cfg, "w") as f:
            json.dump({"units": []}, f)
        rc = fetcher.main(["--config", cfg, "--out-dir", d, "--source", "cog"])
    assert rc == 0
