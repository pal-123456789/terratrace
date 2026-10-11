"""CLI + HTTP-API coverage for the significance / decision-confidence surface.

Dependency-free (plain ``def test_*()``, assert-based, no pytest): exercises the
new ``study --significance`` / ``--n-perm`` flags and the ``confidence``
subcommand of ``terratrace.cli``, plus the ``POST /confidence`` route and the
``significance`` option on ``POST /compare`` of ``terratrace.api``.

NO test here pins a literal ``package_hash`` (that is NumPy-build dependent and
has broken CI before): the assertions are over verdict membership, key presence,
determinism, and the preserved API security posture only. The HTTP server runs
on an ephemeral loopback port, exactly like tests/test_api.py.
"""
import contextlib
import io
import json
import os
import socket
import tempfile
import threading
import urllib.error
import urllib.request

from terratrace import api, cli

# The documented verdict vocabulary (mirrors terratrace.confidence); every
# verdict the engine can emit must be one of these -- never a numeric score.
VALID_VERDICTS = {"robust", "qualified", "fragile", "tie", "indeterminate",
                  "blocked", "not_comparable", "unverified"}


# --- CLI helpers ------------------------------------------------------------

def _exit_code(argv):
    """Run cli.main and normalise the outcome to an int exit code."""
    try:
        rc = cli.main(argv)
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1
    return rc if isinstance(rc, int) else 0


def _run_cli(argv):
    """Run a CLI command, returning (exit_code, captured_stdout)."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = _exit_code(argv)
    return code, buf.getvalue()


def _write_study_json(path, n_boot=60):
    """Dump a study package (with a bootstrap block so a signal is evaluable)."""
    from terratrace import study
    pkg = study.run_study(n_boot=n_boot)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(pkg, fh)
    return pkg


# --- API helpers ------------------------------------------------------------

def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _serve():
    port = _free_port()
    srv = api.make_server("127.0.0.1", port)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def _post(port, path, body=None, raw=None, host=None, timeout=60):
    """POST to the loopback server; return (status, parsed_json_or_None)."""
    data = raw if raw is not None else json.dumps(body or {}).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if host is not None:
        headers["Host"] = host
    req = urllib.request.Request(f"http://127.0.0.1:{port}{path}",
                                 data=data, headers=headers, method="POST")
    try:
        resp = urllib.request.urlopen(req, timeout=timeout)
        return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as exc:
        return exc.code, None


# --- CLI: study --significance / --n-perm -----------------------------------

def test_cli_study_significance_attaches_block_and_prints_verdict():
    """`study --significance` forwards into the study call (study.json gains the
    permutation block) and prints a decision-confidence verdict + rationale."""
    d = tempfile.mkdtemp()
    code, out = _run_cli(["study", "--out", d, "--significance", "--n-perm", "200"])
    assert code == 0, out
    assert "decision_confidence=" in out, out
    assert "confidence_rationale" in out, out
    verdict = out.split("decision_confidence=", 1)[1].split("\n", 1)[0].strip()
    assert verdict in VALID_VERDICTS, verdict
    pkg = json.load(open(os.path.join(d, "study.json"), encoding="utf-8"))
    assert "significance" in pkg, "significance block must be attached"
    assert "recommendation_significant" in pkg["significance"]


def test_cli_study_without_significance_is_legacy_and_still_reports_confidence():
    """Without the flag the artifact carries NO significance key (legacy bytes
    preserved) yet the confidence verdict is still printed (honestly unverified
    when no robustness signal was computed)."""
    d = tempfile.mkdtemp()
    code, out = _run_cli(["study", "--out", d])
    assert code == 0, out
    assert "decision_confidence=" in out, out
    pkg = json.load(open(os.path.join(d, "study.json"), encoding="utf-8"))
    assert "significance" not in pkg
    verdict = out.split("decision_confidence=", 1)[1].split("\n", 1)[0].strip()
    assert verdict == "unverified", verdict


def test_cli_study_default_bytes_match_run_study():
    """The default (no --significance) CLI study package is byte-identical to
    study.run_study() -- the new flags are purely additive (determinism, not a
    pinned literal hash)."""
    from terratrace import study
    from terratrace.provenance import sha256_json
    d = tempfile.mkdtemp()
    code, _ = _run_cli(["study", "--out", d])
    assert code == 0
    pkg = json.load(open(os.path.join(d, "study.json"), encoding="utf-8"))
    assert pkg["package_hash"] == study.run_study()["package_hash"]
    assert sha256_json({k: v for k, v in pkg.items() if k != "package_hash"}) \
        == pkg["package_hash"]


def test_cli_study_rejects_nonpositive_n_perm():
    raised = False
    try:
        cli.main(["study", "--out", tempfile.mkdtemp(), "--significance", "--n-perm", "0"])
    except SystemExit:
        raised = True
    assert raised


# --- CLI: confidence subcommand ---------------------------------------------

def test_cli_confidence_subcommand_text():
    """`confidence --study <json>` prints the verdict, each signal, and caveats."""
    d = tempfile.mkdtemp()
    tmp = os.path.join(d, "study.json")
    _write_study_json(tmp)
    code, out = _run_cli(["confidence", "--study", tmp])
    assert code == 0, out
    assert out.strip(), "expected non-empty output"
    verdict = out.split("verdict:", 1)[1].split("\n", 1)[0].strip()
    assert verdict in VALID_VERDICTS, verdict
    for name in ("bootstrap_non_domination", "significance_vs_runner_up",
                 "lens_stability"):
        assert name in out, name


def test_cli_confidence_subcommand_json():
    """`confidence --study <json> --json` emits a parseable confidence dict."""
    d = tempfile.mkdtemp()
    tmp = os.path.join(d, "study.json")
    _write_study_json(tmp)
    code, out = _run_cli(["confidence", "--study", tmp, "--json"])
    assert code == 0, out
    doc = json.loads(out)
    assert set(doc) >= {"verdict", "signals", "caveats", "state",
                        "recommended_unit", "rationale"}
    assert doc["verdict"] in VALID_VERDICTS
    assert set(doc["signals"]) == {"bootstrap_non_domination",
                                   "significance_vs_runner_up", "lens_stability"}


def test_cli_confidence_missing_file_is_clean_error():
    """A missing study file is a clean non-zero exit, not a traceback."""
    code, _ = _run_cli(["confidence", "--study",
                        os.path.join(tempfile.mkdtemp(), "nope.json")])
    assert code == 2


# --- API: POST /confidence --------------------------------------------------

def test_api_confidence_route_returns_verdict():
    """POST a study package to /confidence -> decision_confidence JSON."""
    from terratrace import study
    srv, port = _serve()
    try:
        pkg = study.run_study(n_boot=60)
        code, out = _post(port, "/confidence", pkg)
        assert code == 200, code
        assert out["verdict"] in VALID_VERDICTS, out["verdict"]
        assert set(out["signals"]) == {"bootstrap_non_domination",
                                       "significance_vs_runner_up", "lens_stability"}
        # The bootstrap signal is evaluated because the package carries n_boot>0.
        b = out["signals"]["bootstrap_non_domination"]
        assert b["evaluated"] is True
        unit = pkg["recommended_unit"]
        assert b["value"] == pkg["bootstrap"]["units"][unit]["nondominated_freq"]
        assert out["state"] == pkg["result_state"]
    finally:
        srv.shutdown()


def test_api_confidence_empty_body_is_unverified():
    """An empty body is a valid (empty) package -> graceful 'unverified'."""
    srv, port = _serve()
    try:
        code, out = _post(port, "/confidence", {})
        assert code == 200, code
        assert out["verdict"] == "unverified"
        assert len(out["caveats"]) == 3
    finally:
        srv.shutdown()


def test_api_confidence_forbidden_host_403():
    """Security posture preserved: a non-loopback Host is rejected (DNS-rebind)."""
    srv, port = _serve()
    try:
        code, _ = _post(port, "/confidence", {}, host="evil.example.com", timeout=10)
        assert code == 403
    finally:
        srv.shutdown()


def test_api_confidence_body_cap_413():
    """Security posture preserved: a body over the 64 KiB cap is rejected 413."""
    srv, port = _serve()
    try:
        oversize = json.dumps({"result_state": "RECOMMEND_FOLLOW_UP",
                               "pad": "x" * (api.MAX_BODY + 1024)}).encode("utf-8")
        code, _ = _post(port, "/confidence", raw=oversize, timeout=10)
        assert code == 413
    finally:
        srv.shutdown()


def test_api_confidence_malformed_and_non_object_bodies_400():
    """Security posture preserved: malformed JSON and non-object bodies are 400."""
    srv, port = _serve()
    try:
        for payload in (b"{not json", b"[1,2,3]"):
            code, _ = _post(port, "/confidence", raw=payload, timeout=10)
            assert code == 400, (payload, code)
    finally:
        srv.shutdown()


# --- API: POST /compare significance option ---------------------------------

def test_api_compare_significance_option_attaches_block():
    """`significance: true` on /compare attaches the permutation block and echoes
    the significance / n_perm params; the recommended unit is also carried."""
    srv, port = _serve()
    try:
        code, out = _post(port, "/compare", {"significance": True, "n_perm": 200})
        assert code == 200, code
        assert out["params"]["significance"] is True
        assert out["params"]["n_perm"] == 200
        result = out["result"]
        assert "significance" in result
        assert "recommendation_significant" in result["significance"]
    finally:
        srv.shutdown()


def test_api_compare_default_has_no_significance_block():
    """Without the option /compare is unchanged: significance defaults off, no
    block attached, and the echoed flag is False (additive, backward-compatible)."""
    srv, port = _serve()
    try:
        code, out = _post(port, "/compare", {"n_boot": 20})
        assert code == 200, code
        assert out["params"]["significance"] is False
        assert "significance" not in out["result"]
        assert "bootstrap" in out["result"]      # existing behaviour intact
    finally:
        srv.shutdown()


def test_api_compare_clamps_n_perm():
    """n_perm is clamped to the interactive MAX_PERM cap (responsiveness guard)."""
    srv, port = _serve()
    try:
        code, out = _post(port, "/compare",
                          {"significance": True, "n_perm": 10 ** 9})
        assert code == 200, code
        assert out["params"]["n_perm"] <= api.MAX_PERM
    finally:
        srv.shutdown()


