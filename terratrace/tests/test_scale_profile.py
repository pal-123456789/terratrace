"""Offline tests for the scale-profile orchestrator script.

yaml-free (driven via ``run_from_config`` with a plain dict), strictly OFFLINE
(only the --synthetic and --dry-run paths), mirroring tests/test_analog_atlas.py.
The REAL download path is intentionally not tested here. The verify command runs
this module with ``sys.modules['yaml'] = None``, proving the script has no
top-level ``import yaml`` (it is imported lazily, only inside _load_config).
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # repo root (terratrace/, scripts/, config/)
SCRIPT = ROOT / "scripts" / "run_scale_profile.py"


def _load_script():
    """Import scripts/run_scale_profile.py as a module (yaml-free: it imports
    PyYAML lazily, only in _load_config)."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("run_scale_profile", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg_with_supports():
    """A single-study-shape config DICT (reference + earth_units) PLUS a top-level
    supports list. Paths are placeholders -- --synthetic generates surfaces in
    memory and never reads them."""
    return {
        "target_support_m": 1000.0,
        "min_valid_fraction": 0.5,
        "reproject": True,
        "supports": [1000, 1500, 2000],
        "reference": {
            "id": "mars_reference", "body": "mars", "is_reference": True,
            "native_posting_m": 463.0, "rights_status": "verified_allowed",
            "bbox": [120.0, -5.0, 130.0, 5.0], "path": "data/mars/mola_463m.tif"},
        "earth_units": [
            {"id": "earth_a", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-115.80, 36.00, -115.40, 36.40], "path": "data/earth/a_cop30.tif"},
            {"id": "earth_b", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-113.60, 43.30, -113.30, 43.60], "path": "data/earth/b_cop30.tif"},
        ],
    }


def test_scale_profile_synthetic_writes_bundle():
    mod = _load_script()
    cfg = _cfg_with_supports()
    out = tempfile.mkdtemp(prefix="scale_syn_")
    rc = mod.run_from_config(cfg, out=out, synthetic=True)
    assert rc == 0, f"synthetic returned {rc!r}"
    for name in ("scale_profile.json", "scale_profile.md"):
        assert os.path.exists(os.path.join(out, name)), f"missing {name}"

    with open(os.path.join(out, "scale_profile.json"), encoding="utf-8") as fh:
        payload = json.load(fh)
    prof = payload["profile"]
    assert prof["supports"] == [1000.0, 1500.0, 2000.0], prof["supports"]
    assert prof["reference_id"] == "mars_reference"
    assert set(prof["candidates"]) == {"earth_a", "earth_b"}
    for c in prof["candidates"]:
        assert len(prof["per_candidate"][c]["distance"]) == 3, c
        assert len(prof["per_candidate"][c]["layer"]) == 3, c
    assert len(prof["best_by_support"]) == 3
    assert "signature" in payload and "scale_stable" in payload["signature"]
    assert isinstance(payload["signature"]["scale_stable"], bool)


def test_scale_profile_dry_run_offline():
    # Preflight is fully offline; it returns 0 (clean) / 2 (problems), nothing else.
    mod = _load_script()
    rc = mod.run_from_config(_cfg_with_supports(), dry_run=True)
    assert rc in (0, 2), f"dry-run exit code was {rc!r}"


def test_supports_default_when_absent():
    # Omitting `supports:` falls back to the script's DEFAULT_SUPPORTS sweep.
    mod = _load_script()
    cfg = _cfg_with_supports()
    del cfg["supports"]
    out = tempfile.mkdtemp(prefix="scale_def_")
    rc = mod.run_from_config(cfg, out=out, synthetic=True)
    assert rc == 0, f"synthetic returned {rc!r}"
    with open(os.path.join(out, "scale_profile.json"), encoding="utf-8") as fh:
        prof = json.load(fh)["profile"]
    assert prof["supports"] == [1000.0, 1500.0, 2000.0, 3000.0, 4000.0], prof["supports"]


if __name__ == "__main__":
    for _name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[_name]()
    print("OK")
