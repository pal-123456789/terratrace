"""Offline tests for the one-command analog-study orchestrator.

Dependency-free (plain top-level ``test_*`` + ``assert``), and strictly OFFLINE:
only the --synthetic (deterministic surfaces) and --dry-run (preflight) paths are
exercised, so no network call and no rasterio import ever happens. The REAL
download path is intentionally not tested here.
"""
import importlib.util
import json
import os
import pathlib
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                                   # repo root (holds terratrace/, scripts/, config/)
SCRIPT = ROOT / "scripts" / "run_real_analog_study.py"
CONFIG = ROOT / "config" / "real_multibody.example.yml"

# The full set of decision states the engine can emit (terratrace.decision.STATES).
_VALID_STATES = {"RECOMMEND_FOLLOW_UP", "TIE", "INDETERMINATE", "NOT_COMPARABLE", "BLOCKED"}


def _load_orchestrator():
    """Import scripts/run_real_analog_study.py as a module.

    The script inserts the repo root onto sys.path at import time, so its own
    ``from terratrace import ...`` resolves; we also insert it here so this test
    file can be run from anywhere.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location("run_real_analog_study", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _call_main(argv):
    """Run ``main(argv)``, returning its exit code whether it returns a code or
    raises ``SystemExit`` (argparse / --dry-run). ``None`` is treated as 0."""
    mod = _load_orchestrator()
    try:
        rc = mod.main(argv)
    except SystemExit as exc:
        rc = exc.code
    return 0 if rc is None else rc


def test_synthetic_end_to_end():
    out = tempfile.mkdtemp(prefix="ras_syn_")
    rc = _call_main(["--config", str(CONFIG), "--synthetic", "--out", out])
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


def test_dry_run_offline():
    # Preflight is fully offline; it must exit cleanly (0 = clean, 2 = problems)
    # and nothing else.
    rc = _call_main(["--config", str(CONFIG), "--dry-run"])
    assert rc in (0, 2), f"dry-run exit code was {rc!r}"


if __name__ == "__main__":
    for _name in sorted(n for n in dir() if n.startswith("test_")):
        globals()[_name]()
    print("OK")
