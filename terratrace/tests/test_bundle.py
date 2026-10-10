"""One-command deliverable-bundle tests (dependency-free, assert-based).

Mirrors the style of tests/test_report.py: plain ``test_*`` functions, no
pytest required, fast (default synthetic study, n_boot=0). Temp dirs are made
with tempfile.mkdtemp and removed in a finally block.
"""
import hashlib
import os
import re
import shutil
import tempfile

from terratrace import bundle, study

_RENDERED = ("study.json", "report.md", "report.html", "REFERENCES.md", "viewer.html")
_ALL_FILES = _RENDERED + ("CHECKSUMS.txt",)
_HEX64 = re.compile(r"^[0-9a-f]{64}$")


def _read_bytes(path):
    with open(path, "rb") as fh:
        return fh.read()


def test_export_writes_all_six_files_nonempty():
    tmp = tempfile.mkdtemp(prefix="tt_bundle_")
    try:
        bundle.export_bundle(study.run_study(), tmp)
        for name in _ALL_FILES:
            path = os.path.join(tmp, name)
            assert os.path.isfile(path), f"missing {name}"
            assert os.path.getsize(path) > 0, f"empty {name}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_html_artifacts_are_html_documents():
    tmp = tempfile.mkdtemp(prefix="tt_bundle_")
    try:
        bundle.export_bundle(study.run_study(), tmp)
        for name in ("report.html", "viewer.html"):
            text = _read_bytes(os.path.join(tmp, name)).decode("utf-8")
            assert text.lstrip().lower().startswith("<!doctype html"), name
            assert "<html" in text.lower(), name
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_checksums_match_file_bytes():
    tmp = tempfile.mkdtemp(prefix="tt_bundle_")
    try:
        bundle.export_bundle(study.run_study(), tmp)
        text = _read_bytes(os.path.join(tmp, "CHECKSUMS.txt")).decode("utf-8")
        lines = [ln for ln in text.splitlines() if ln.strip()]
        assert len(lines) == len(_RENDERED), (len(lines), _RENDERED)
        listed = {}
        for ln in lines:
            digest, name = ln.split("  ", 1)  # "<sha256>  <filename>"
            listed[name] = digest
        for name in _RENDERED:
            assert name in listed, f"{name} not listed in CHECKSUMS.txt"
            actual = hashlib.sha256(_read_bytes(os.path.join(tmp, name))).hexdigest()
            assert listed[name] == actual, f"checksum mismatch for {name}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_manifest_shape_and_package_hash():
    tmp = tempfile.mkdtemp(prefix="tt_bundle_")
    try:
        pkg = study.run_study()
        manifest = bundle.export_bundle(pkg, tmp)
        assert isinstance(manifest, dict)
        files = manifest["files"]
        assert isinstance(files, dict) and files
        for name in _RENDERED:
            assert name in files, f"{name} missing from manifest files"
        for name, info in files.items():
            assert info["bytes"] > 0, f"{name} non-positive bytes"
            assert _HEX64.match(info["sha256"]), f"{name} bad sha256 {info['sha256']}"
            assert info["bytes"] == os.path.getsize(os.path.join(tmp, name)), name
        assert manifest["package_hash"] == pkg["package_hash"]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_export_is_deterministic_for_fixed_package():
    pkg = study.run_study()
    a = tempfile.mkdtemp(prefix="tt_bundle_a_")
    b = tempfile.mkdtemp(prefix="tt_bundle_b_")
    try:
        ma = bundle.export_bundle(pkg, a)
        mb = bundle.export_bundle(pkg, b)
        # Spec requires at least study.json + report.md + report.html; a fixed
        # package renders deterministically everywhere, so assert all five.
        for name in _RENDERED:
            ha = hashlib.sha256(_read_bytes(os.path.join(a, name))).hexdigest()
            hb = hashlib.sha256(_read_bytes(os.path.join(b, name))).hexdigest()
            assert ha == hb, f"{name} differs across exports"
            assert ma["files"][name]["sha256"] == ha, f"{name} manifest/disk mismatch (a)"
            assert mb["files"][name]["sha256"] == hb, f"{name} manifest/disk mismatch (b)"
    finally:
        shutil.rmtree(a, ignore_errors=True)
        shutil.rmtree(b, ignore_errors=True)
