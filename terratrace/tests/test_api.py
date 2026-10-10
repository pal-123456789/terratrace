"""HTTP API fixtures (stdlib server on an ephemeral loopback port)."""
import json
import socket
import threading
import urllib.error
import urllib.request

from terratrace import api


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


def test_health():
    srv, port = _serve()
    try:
        h = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/health", timeout=5).read())
        assert h["status"] == "ok" and h["service"] == "terratrace"
        assert "version" in h
    finally:
        srv.shutdown()


def test_compare_runs_with_bootstrap():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/compare",
            data=json.dumps({"n_boot": 40}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert r["params"]["n_boot"] == 40
        assert r["result"]["result_state"] in (
            "RECOMMEND_FOLLOW_UP", "TIE", "INDETERMINATE", "NOT_COMPARABLE", "BLOCKED")
        assert "bootstrap" in r["result"]
    finally:
        srv.shutdown()


def test_unknown_route_404():
    srv, port = _serve()
    try:
        raised = False
        try:
            urllib.request.urlopen(f"http://127.0.0.1:{port}/nope", timeout=5)
        except urllib.error.HTTPError as e:
            raised = (e.code == 404)
        assert raised
    finally:
        srv.shutdown()


def test_compare_clamps_bad_input():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/compare",
            data=json.dumps({"n_boot": 999999, "target_support_m": -5}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert r["params"]["n_boot"] <= 2000
        assert r["params"]["target_support_m"] >= 1.0
    finally:
        srv.shutdown()


def test_get_study_has_contract_keys():
    srv, port = _serve()
    try:
        r = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/study", timeout=30).read())
        for k in ("profile", "result_state", "baseline_vectors", "evidence_graph"):
            assert k in r
    finally:
        srv.shutdown()


def test_malformed_and_non_object_bodies_400():
    srv, port = _serve()
    try:
        for payload in (b"{not json", b"[1,2,3]"):
            req = urllib.request.Request(f"http://127.0.0.1:{port}/compare",
                                         data=payload, method="POST")
            code = 0
            try:
                urllib.request.urlopen(req, timeout=10)
            except urllib.error.HTTPError as e:
                code = e.code
            assert code == 400, (payload, code)
    finally:
        srv.shutdown()


def test_forbidden_host_is_403():
    srv, port = _serve()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/health",
                                     headers={"Host": "evil.example.com"})
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 403
    finally:
        srv.shutdown()


def test_post_wrong_path_404():
    srv, port = _serve()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/nope",
                                     data=b"{}", method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 404
    finally:
        srv.shutdown()


def test_bodies_lists_bodies_and_sources():
    srv, port = _serve()
    try:
        r = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{port}/bodies", timeout=10).read())
        assert isinstance(r, dict)
        assert "mars" in r["bodies"] and "moon" in r["bodies"]
        assert isinstance(r["sources"], list) and r["sources"]
        s0 = r["sources"][0]
        for k in ("id", "body", "product", "native_resolution_m", "key_required"):
            assert k in s0, k
    finally:
        srv.shutdown()


def test_validate_all_passed():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/validate",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        for k in ("passed", "failed", "all_passed", "package_hash"):
            assert k in r, k
        assert r["all_passed"] is True
        assert r["failed"] == 0
    finally:
        srv.shutdown()


def test_batch_core_mode():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/batch",
            data=json.dumps({"decision_modes": ["core"]}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r, dict)
        assert "consensus_shortlist" in r and "per_candidate" in r
        assert isinstance(r["per_candidate"], dict) and r["per_candidate"]
        assert "package_hash" in r
    finally:
        srv.shutdown()


def test_report_renders_markdown():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/report",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r.get("markdown"), str) and r["markdown"].strip()
        assert "SCOPE" in r["markdown"] or "prohibited" in r["markdown"].lower()
        assert r.get("package_hash")
    finally:
        srv.shutdown()


def test_new_post_route_forbidden_host_403():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/batch",
            data=b"{}", headers={"Host": "evil.example.com"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 403
    finally:
        srv.shutdown()
