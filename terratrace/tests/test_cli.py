"""CLI fixtures."""
import json
import os
import tempfile

from terratrace import cli
from terratrace.provenance import sha256_json


def test_cli_writes_study_and_checksums():
    d = tempfile.mkdtemp()
    rc = cli.main(["--out", d])
    assert rc == 0
    study = json.load(open(os.path.join(d, "study.json"), encoding="utf-8"))
    assert "result_state" in study and "package_hash" in study
    manifest = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    # each recorded checksum matches a recompute
    assert manifest["artifacts"]["study.json"] == sha256_json(study)


def test_cli_rejects_nonpositive_support():
    raised = False
    try:
        cli.main(["--out", tempfile.mkdtemp(), "--target-support-m", "0"])
    except SystemExit:
        raised = True
    assert raised
