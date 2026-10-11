"""Offline tests for the one-command analog-study orchestrator.

Dependency-free (plain top-level ``test_*`` + ``assert``), strictly OFFLINE, and
IMPORTANTLY yaml-free: the orchestration is driven through ``run_from_config``
with a plain Python dict, so neither PyYAML (a requirements-real extra, absent in
the NumPy-only CI env) nor rasterio nor any network is needed. Only the
--synthetic (deterministic surfaces) and --dry-run (preflight) paths are
exercised; the REAL download path is intentionally not tested here.
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # repo root (terratrace/, scripts/, config/)
SCRIPT = ROOT / "scripts" / "run_real_analog_study.py"
CONFIG = ROOT / "config" / "real_multibody.example.yml"

# The full set of decision states the engine can emit (terratrace.decision.STATES).
_VALID_STATES = {"RECOMMEND_FOLLOW_UP", "TIE", "INDETERMINATE", "NOT_COMPARABLE", "BLOCKED"}


def _load_orchestrator():
    """Import scripts/run_real_analog_study.py as a module.

    The script no longer imports PyYAML at module top (yaml is lazy, only in
    _load_config), so importing it here is yaml-free; it also inserts the repo
    root onto sys.path so its ``from terratrace import ...`` resolves.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("run_real_analog_study", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _cfg():
    """A compact, valid multi-body config DICT (no YAML needed) with the depth
    flags ON and small resampling counts for a fast offline run."""
    return {
        "target_support_m": 1000.0,
        "min_valid_fraction": 0.5,
        "reproject": True,
        "decision_metrics": "extended",
        "n_boot": 40,
        "significance": True,
        "n_perm": 120,
        "landform": True,
        "terrain_spectra": True,
        "previews": True,
        "reference": {
            "id": "mars_reference", "body": "mars", "is_reference": True,
            "rights_status": "verified_allowed", "native_posting_m": 463.0,
            "bbox": [120.0, -5.0, 130.0, 5.0], "path": "data/mars/mola_463m.tif",
        },
        "earth_units": [
            {"id": "earth_a", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-115.80, 36.00, -115.40, 36.40], "path": "data/earth/a_cop30.tif"},
            {"id": "earth_b", "body": "earth", "demtype": "COP30",
             "native_posting_m": 30.0, "rights_status": "verified_allowed",
             "bbox": [-113.60, 43.30, -113.30, 43.60], "path": "data/earth/b_cop30.tif"},
        ],
    }


def test_synthetic_end_to_end():
    mod = _load_orchestrator()
    out = tempfile.mkdtemp(prefix="ras_syn_")
    rc = mod.run_from_config(_cfg(), out=out, synthetic=True)
    assert rc == 0, f"synthetic run returned {rc!r}"

    for name in ("study.json", "report.html", "confidence.json"):
        assert os.path.exists(os.path.join(out, name)), f"bundle missing {name}"

    with open(os.path.join(out, "study.json"), encoding="utf-8") as fh:
        pkg = json.load(fh)
    # The config's depth flags (significance / landform / terrain_spectra) must
    # have been honored and shown up as package blocks.
    for key in ("significance", "landform", "spectral", "anisotropy"):
        assert key in pkg, f"depth flag not honored: missing package key {key!r}"
    assert pkg.get("result_state") in _VALID_STATES, pkg.get("result_state")

    with open(os.path.join(out, "confidence.json"), encoding="utf-8") as fh:
        conf = json.load(fh)
    assert conf.get("verdict"), "confidence.json has no verdict"


def test_ablation_synthetic():
    # One run, all five decision lenses, SAME offline surfaces. Fully offline
    # (no yaml / rasterio / network): --synthetic ablation uses _synthetic_inputs.
    mod = _load_orchestrator()
    out = tempfile.mkdtemp(prefix="ras_abl_")
    rc = mod.run_from_config(_cfg(), out=out, synthetic=True, ablation=True)
    assert rc == 0, f"ablation run returned {rc!r}"

    abl_path = os.path.join(out, "ablation.json")
    assert os.path.exists(abl_path), "ablation.json not written"
    with open(abl_path, encoding="utf-8") as fh:
        abl = json.load(fh)
    rows = abl["lenses"]
    assert len(rows) == 5, f"expected 5 lens rows, got {len(rows)}"
    assert {r["lens"] for r in rows} == {
        "core", "extended", "geomorphic", "landform", "texture"}
    for r in rows:
        assert r["result_state"] in _VALID_STATES, r["result_state"]


def test_decision_metrics_override_synthetic():
    # --decision-metrics overrides the config's lens ("extended") for the single
    # study; the resulting package profile must record the override.
    mod = _load_orchestrator()
    out = tempfile.mkdtemp(prefix="ras_dm_")
    rc = mod.run_from_config(_cfg(), out=out, synthetic=True, decision_metrics="core")
    assert rc == 0, f"override run returned {rc!r}"
    with open(os.path.join(out, "study.json"), encoding="utf-8") as fh:
        pkg = json.load(fh)
    assert pkg["profile"]["decision_metrics"] == "core", pkg["profile"].get("decision_metrics")


def test_dry_run_offline():
    # Preflight is fully offline; it returns 0 (clean) / 2 (problems), nothing else.
    mod = _load_orchestrator()
    rc = mod.run_from_config(_cfg(), dry_run=True)
    assert rc in (0, 2), f"dry-run exit code was {rc!r}"


def test_example_config_parses_when_yaml_available():
    # Validates the SHIPPED YAML example end-to-end only where PyYAML is
    # installed (requirements-real); in the NumPy-only CI env this is skipped
    # (treated as a pass) rather than failing on a missing optional dependency.
    try:
        import yaml  # noqa: F401
    except ImportError:
        return
    mod = _load_orchestrator()
    cfg = mod._load_config(str(CONFIG))
    assert isinstance(cfg, dict)
    assert "reference" in cfg and "earth_units" in cfg
    assert cfg["reference"].get("is_reference") is True


if __name__ == "__main__":
    for _name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[_name]()
    print("OK")
