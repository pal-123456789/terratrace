"""Offline tests for the TerraTrace analog-atlas orchestrator.

Dependency-free (plain top-level ``test_*`` + ``assert``), strictly OFFLINE, and
IMPORTANTLY yaml-free: the atlas is driven through ``run_from_config`` with a plain
Python dict, so neither PyYAML (a requirements-real extra, absent in the NumPy-only
CI env) nor rasterio nor any network is needed. Only the --synthetic
(deterministic surfaces) and --dry-run (preflight) paths are exercised; the REAL
download path is intentionally not tested here.

CI-safety is asserted directly by the verify command, which runs these tests with
``sys.modules['yaml'] = None`` -- importing and running them must still pass, proving
the script has no top-level ``import yaml``.
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # repo root (terratrace/, scripts/, config/)
SCRIPT = ROOT / "scripts" / "run_analog_atlas.py"


def _load_atlas():
    """Import scripts/run_analog_atlas.py as a module.

    The script imports PyYAML lazily (only in _load_config), so importing it here
    is yaml-free; it also inserts the repo root onto sys.path so its
    ``from terratrace import ...`` resolves.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("run_analog_atlas", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg():
    """A compact, valid atlas config DICT (no YAML needed): 2 synthetic Mars
    reference windows + 3 Earth candidates. Paths are placeholders -- the
    --synthetic path generates surfaces in-memory and never reads them."""
    return {
        "target_support_m": 1000.0,
        "min_valid_fraction": 0.5,
        "reproject": True,
        "references": [
            {"id": "mars_sw", "body": "mars", "is_reference": True,
             "native_posting_m": 463.0, "rights_status": "verified_allowed",
             "bbox": [120.0, -5.0, 125.0, 0.0], "path": "data/mars/mola_463m.tif"},
            {"id": "mars_ne", "body": "mars", "is_reference": True,
             "native_posting_m": 463.0, "rights_status": "verified_allowed",
             "bbox": [125.0, 0.0, 130.0, 5.0], "path": "data/mars/mola_463m.tif"},
        ],
        "candidates": [
            {"id": "earth_a", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-115.80, 36.00, -115.40, 36.40], "path": "data/earth/a_cop30.tif"},
            {"id": "earth_b", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-113.60, 43.30, -113.30, 43.60], "path": "data/earth/b_cop30.tif"},
            {"id": "earth_c", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-78.60, -0.20, -78.30, 0.10], "path": "data/earth/c_cop30.tif"},
        ],
    }


def test_atlas_synthetic():
    # Deterministic offline surfaces -> the SAME batch engine -> a real catalog.
    mod = _load_atlas()
    cfg = _cfg()
    out = tempfile.mkdtemp(prefix="atlas_syn_")
    rc = mod.run_from_config(cfg, out=out, synthetic=True)
    assert rc == 0, f"synthetic atlas returned {rc!r}"

    for name in ("atlas.json", "atlas.md"):
        assert os.path.exists(os.path.join(out, name)), f"catalog missing {name}"

    with open(os.path.join(out, "atlas.json"), encoding="utf-8") as fh:
        report = json.load(fh)
    n_ref = len(cfg["references"])
    n_cand = len(cfg["candidates"])
    assert "per_candidate" in report, "report missing per_candidate"
    assert len(report["robust_ordering"]) == n_cand, report["robust_ordering"]
    assert set(report["robust_ordering"]) == {c["id"] for c in cfg["candidates"]}
    assert "consensus_shortlist" in report, "report missing consensus_shortlist"
    assert len(report["decision_modes"]) == 4, report["decision_modes"]
    # Every (reference x lens) pairing is one cell: n_ref references x 4 lenses.
    assert report["n_cells"] == n_ref * 4, report["n_cells"]
    # Each candidate carries the per-candidate robustness synthesis fields.
    for c in cfg["candidates"]:
        pc = report["per_candidate"][c["id"]]
        for key in ("layer1_frequency", "recommended_frequency", "mean_layer", "cells_ranked"):
            assert key in pc, f"per_candidate[{c['id']}] missing {key}"


def test_atlas_dry_run_offline():
    # Preflight is fully offline; it returns 0 (clean) / 2 (problems), nothing else.
    mod = _load_atlas()
    rc = mod.run_from_config(_cfg(), dry_run=True)
    assert rc in (0, 2), f"dry-run exit code was {rc!r}"


if __name__ == "__main__":
    for _name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[_name]()
    print("OK")
