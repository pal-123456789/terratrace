"""CLI fixtures: legacy study call + unified subcommand dispatcher."""
import contextlib
import io
import json
import os
import tempfile

from terratrace import cli
from terratrace.provenance import sha256_json


def _exit_code(argv):
    """Run cli.main and normalise the outcome to an int exit code, whether it
    returns an int or raises SystemExit (whose code may be int, None, or str)."""
    try:
        rc = cli.main(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    return rc if isinstance(rc, int) else 0


def _write_study_json(path):
    """Dump a small default study package to `path` (JSON) and return it."""
    from terratrace import study
    pkg = study.run_study()
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pkg, fh)
    return pkg


def test_cli_writes_study_and_checksums():
    d = tempfile.mkdtemp()
    rc = cli.main(["--out", d])
    assert rc == 0
    study = json.load(open(os.path.join(d, "study.json"), encoding="utf-8"))
    assert "result_state" in study and "package_hash" in study
    manifest = json.load(open(os.path.join(d, "manifest.json"), encoding="utf-8"))
    # each recorded checksum matches a recompute
    assert manifest["artifacts"]["study.json"] == sha256_json(study)


def test_cli_study_subcommand_matches_legacy():
    # The explicit `study` subcommand must do exactly what the legacy call does.
    d = tempfile.mkdtemp()
    rc = cli.main(["study", "--out", d])
    assert rc == 0
    study = json.load(open(os.path.join(d, "study.json"), encoding="utf-8"))
    assert "result_state" in study and "package_hash" in study
    assert os.path.exists(os.path.join(d, "manifest.json"))
    assert os.path.exists(os.path.join(d, "checksums.txt"))


def test_cli_rejects_nonpositive_support():
    raised = False
    try:
        cli.main(["--out", tempfile.mkdtemp(), "--target-support-m", "0"])
    except SystemExit:
        raised = True
    assert raised


def test_cli_validate_subcommand_passes():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["validate"])
    assert code == 0
    assert "all_passed" in buf.getvalue()


def test_cli_version_subcommand_prints_and_exits_zero():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["version"])
    assert code == 0
    assert buf.getvalue().strip() != ""


def test_cli_help_exits_zero():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["--help"])
    assert code == 0
    assert buf.getvalue().strip() != ""


def test_cli_unknown_subcommand_errors():
    err = io.StringIO()
    raised = False
    code = None
    try:
        with contextlib.redirect_stderr(err):
            code = cli.main(["definitely-not-a-command"])
    except SystemExit as exc:
        raised = True
        code = exc.code
    # A clean failure: either SystemExit, or a nonzero int return value.
    assert raised or (isinstance(code, int) and code != 0)


def test_cli_report_html_subcommand_writes_html():
    d = tempfile.mkdtemp()
    tmp_json = os.path.join(d, "study.json")
    tmp_html = os.path.join(d, "study_report.html")
    _write_study_json(tmp_json)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["report-html", "--study", tmp_json, "--out", tmp_html])
    assert code == 0
    assert os.path.exists(tmp_html)
    with open(tmp_html, encoding="utf-8") as fh:
        head = fh.read(64)
    assert head.lower().startswith("<!doctype html")


def test_cli_dossier_subcommand_unit():
    d = tempfile.mkdtemp()
    tmp_json = os.path.join(d, "study.json")
    _write_study_json(tmp_json)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["dossier", "--study", tmp_json, "--unit", "earth_close"])
    assert code == 0
    assert buf.getvalue().strip() != ""


def test_cli_dossier_subcommand_summary():
    d = tempfile.mkdtemp()
    tmp_json = os.path.join(d, "study.json")
    _write_study_json(tmp_json)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["dossier", "--study", tmp_json])
    assert code == 0
    assert buf.getvalue().strip() != ""


def test_cli_references_subcommand_prints_and_exits_zero():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["references"])
    assert code == 0
    assert buf.getvalue().strip() != ""


def test_cli_references_subcommand_out_writes_file():
    d = tempfile.mkdtemp()
    out = os.path.join(d, "references.md")
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["references", "--out", out])
    assert code == 0
    assert os.path.exists(out)
    with open(out, encoding="utf-8") as fh:
        assert fh.read().strip() != ""


def test_cli_sensitivity_subcommand_exits_zero():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["sensitivity"])
    assert code == 0
    assert buf.getvalue().strip() != ""


def test_cli_classify_subcommand_exits_zero():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(["classify"])
    assert code == 0
    assert buf.getvalue().strip() != ""
