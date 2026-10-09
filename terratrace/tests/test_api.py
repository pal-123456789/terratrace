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
