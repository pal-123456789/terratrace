"""HTTP API fixtures (stdlib server on an ephemeral loopback port)."""
import json
import socket
import threading
import urllib.error
import urllib.request

from terratrace import api, synthetic


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def _small_tile(shape=(24, 24)):
    """A small, deterministic, well-conditioned synthetic elevation tile as a
    nested Python list (JSON-ready, no numpy/rasterio in the request). Slope +
    central dome + seeded roughness keep every descriptor non-degenerate while the
    body stays well under the 64 KiB cap."""
    z = (synthetic.plane(shape, slope_x=0.03, slope_y=0.01)
         + synthetic.gaussian_hill(shape, amplitude=12.0, sigma=6.0)
         + synthetic.rough_field(shape, amplitude=1.5, seed=7))
    return z.tolist()


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


def test_dossier_all_units_default_body():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/dossier",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r, dict) and "earth_close" in r
        d = r["earth_close"]
        for k in ("is_recommended", "eligible", "distances"):
            assert k in d, k
    finally:
        srv.shutdown()


def test_dossier_single_unit():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/dossier",
            data=json.dumps({"unit": "earth_close"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r, dict)
        assert r.get("unit") == "earth_close"
        assert "is_recommended" in r and "eligible" in r
    finally:
        srv.shutdown()


def test_dossier_unknown_unit_is_400():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/dossier",
            data=json.dumps({"unit": "does_not_exist"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=60)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 400
    finally:
        srv.shutdown()


def test_report_html_renders_document():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/report.html",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        resp = urllib.request.urlopen(req, timeout=60)
        ctype = resp.headers.get("Content-Type", "")
        body = resp.read().decode("utf-8")
        assert "text/html" in ctype, ctype
        assert body.lstrip().lower().startswith("<!doctype html")
        assert "SCOPE" in body or "prohibited" in body.lower()
    finally:
        srv.shutdown()


def test_dossier_forbidden_host_403():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/dossier",
            data=b"{}", headers={"Host": "evil.example.com"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 403
    finally:
        srv.shutdown()


def test_references_lists_catalog_credits():
    srv, port = _serve()
    try:
        r = json.loads(urllib.request.urlopen(
            f"http://127.0.0.1:{port}/references", timeout=10).read())
        assert isinstance(r, dict)
        refs = r["references"]
        assert isinstance(refs, list) and refs            # non-empty list
        for rec in refs:
            assert isinstance(rec, dict)
            assert rec.get("citation")                     # every credit is attributed
            assert rec.get("license")                      # and carries a licence
    finally:
        srv.shutdown()


def test_sensitivity_default_body_is_stable():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/sensitivity",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r, dict)
        assert isinstance(r["recommendation_stable"], bool)
        assert r["recommendation_stable"] is True          # clear-winner scene -> stable
        per_lens = r["per_lens"]
        assert isinstance(per_lens, dict) and per_lens
        assert set(per_lens) == {"core", "extended", "geomorphic"}
        assert r["recommended_units"] == ["near"]          # the sole analog under every lens
    finally:
        srv.shutdown()


def test_classify_default_body_distinguishes_terrains():
    from terratrace import terrain_classify
    rough_type = terrain_classify.TYPES[-1]                # documented most-rugged label
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/classify",
            data=json.dumps({}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        classes = r["classes"]
        assert isinstance(classes, dict)
        for label in ("reference", "smooth", "rough"):
            assert label in classes, label
        assert classes["rough"] == rough_type              # rough terrain -> rugged type
        assert classes["smooth"] != rough_type             # flat terrain is NOT the rough type
        assert classes["smooth"] != classes["rough"]       # smooth and rough differ
    finally:
        srv.shutdown()


def test_sensitivity_forbidden_host_403():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/sensitivity",
            data=b"{}", headers={"Host": "evil.example.com"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 403
    finally:
        srv.shutdown()


# __APPEND_BANK_TRANSECT_TESTS__


def test_bank_returns_descriptor_bank():
    srv, port = _serve()
    try:
        body = json.dumps({"z": _small_tile(), "dx": 10.0}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/bank", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r, dict)
        for k in ("slope", "variogram", "melton_relief", "fabric_eigen"):
            assert k in r, k
        assert set(r["slope"]) >= {"mean", "std", "p10", "p50", "p90"}
    finally:
        srv.shutdown()


def test_bank_missing_z_is_400():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/bank",
            data=json.dumps({"dx": 10.0}).encode("utf-8"),
            headers={"Content-Type": "application/json"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 400
    finally:
        srv.shutdown()


def test_bank_malformed_body_is_400():
    # same code as the sibling POST endpoints for a malformed JSON body
    srv, port = _serve()
    try:
        req = urllib.request.Request(f"http://127.0.0.1:{port}/bank",
                                     data=b"{not json", method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 400
    finally:
        srv.shutdown()


# __APPEND_BANK_TRANSECT_TESTS_2__


def test_bank_oversize_body_is_413():
    # body larger than MAX_BODY -> rejected on Content-Length, like every POST
    srv, port = _serve()
    try:
        payload = b'{"z":' + b'0' * (api.MAX_BODY + 1024) + b'}'
        req = urllib.request.Request(f"http://127.0.0.1:{port}/bank",
                                     data=payload, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 413
    finally:
        srv.shutdown()


def test_bank_forbidden_host_403():
    srv, port = _serve()
    try:
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/bank",
            data=b"{}", headers={"Host": "evil.example.com"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=10)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 403
    finally:
        srv.shutdown()


def test_transect_returns_signature():
    srv, port = _serve()
    try:
        body = json.dumps({"z": _small_tile(), "p0": [2, 2], "p1": [21, 21],
                           "dx": 10.0}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/transect", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        r = json.loads(urllib.request.urlopen(req, timeout=60).read())
        assert isinstance(r, dict)
        assert "mean_slope" in r
        for k in ("length_m", "relief_m", "max_slope", "elev_gain_m"):
            assert k in r, k
    finally:
        srv.shutdown()


def test_transect_bad_points_is_400():
    srv, port = _serve()
    try:
        body = json.dumps({"z": _small_tile(), "p0": [2, 2], "p1": [21]}).encode("utf-8")
        req = urllib.request.Request(
            f"http://127.0.0.1:{port}/transect", data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        code = 0
        try:
            urllib.request.urlopen(req, timeout=30)
        except urllib.error.HTTPError as e:
            code = e.code
        assert code == 400
    finally:
        srv.shutdown()
