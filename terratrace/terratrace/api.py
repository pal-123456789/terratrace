"""Minimal, dependency-free HTTP API for TerraTrace.

Exposes the engine over HTTP using only the Python standard library (no Flask/
FastAPI needed), so it runs anywhere Python does. Endpoints:

    GET  /health            -> liveness + version
    GET  /study             -> the canonical synthetic study package (JSON)
    GET  /bodies            -> supported reference bodies + data-source registry
    POST /compare           -> run a synthetic study with validated parameters
                               body: {"target_support_m": float, "n_boot": int}
    POST /validate          -> run the scientific-correctness validation suite
    POST /batch             -> a small synthetic cross-reference batch study
                               body: {"decision_modes": ["core", ...]}
    POST /report            -> run_study + render a publication-grade Markdown report
                               body: {"target_support_m": float, "n_boot": int}

SECURITY: this server is UNAUTHENTICATED and binds to 127.0.0.1 (localhost) by
default. Do not expose it to a network without putting authentication and rate
limiting in front of it. Real-DEM comparisons stay in the CLI (they need large
files + rasterio); this API serves the reproducible synthetic engine and the
canonical study.
"""
from __future__ import annotations

import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import __version__, study, catalog, validation, batch, synthetic

MAX_BOOT = 500             # interactive responsiveness cap for the HTTP endpoint
                           # (~7 s worst case); the library accepts any n_boot offline.
MAX_BODY = 1 << 16          # 64 KiB cap on request bodies
LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}
ROUTES = ["GET /health", "GET /study", "GET /bodies",
          "POST /compare", "POST /validate", "POST /batch", "POST /report"]
POST_ROUTES = ("/compare", "/validate", "/batch", "/report")


def _clamp(value, lo, hi, default):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


def _synthetic_batch(shape=(48, 48)):
    """Build a small, deterministic cross-reference batch: two Mars-style
    references and three Earth-style candidates (one deliberately far), mirroring
    study._unit_grid so the synthetic morphology is realistic yet tiny enough for
    a fast API call. Returns (units, references, candidates)."""
    def grid(slope_x, slope_y, amp, seed):
        return synthetic.plane(shape, slope_x, slope_y) + synthetic.rough_field(shape, amp, seed)
    units = {
        "mars_ref_a": grid(0.12, 0.05, 0.60, 1),
        "mars_ref_b": grid(0.14, 0.04, 0.70, 5),
        "earth_candidate_a": grid(0.11, 0.06, 0.65, 2),
        "earth_candidate_b": grid(0.13, 0.05, 0.60, 7),
        "earth_candidate_far": grid(0.30, 0.02, 2.20, 3),
    }
    references = ["mars_ref_a", "mars_ref_b"]
    candidates = ["earth_candidate_a", "earth_candidate_b", "earth_candidate_far"]
    return units, references, candidates


class Handler(BaseHTTPRequestHandler):
    server_version = "TerraTrace/" + __version__

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, *args):
        pass  # quiet

    def _host_ok(self):
        # Defend against DNS-rebinding: only serve requests whose Host is loopback.
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in LOOPBACK or host.startswith("127.")

    def do_GET(self):
        try:
            if not self._host_ok():
                return self._send(403, {"error": "forbidden host"})
            route = self.path.split("?")[0]
            if route == "/health":
                return self._send(200, {"status": "ok", "service": "terratrace",
                                        "version": __version__, "routes": ROUTES})
            if route == "/study":
                return self._send(200, study.run_study())
            if route == "/bodies":
                return self._send(200, self._bodies())
            return self._send(404, {"error": "not found", "routes": ROUTES})
        except Exception:
            return self._send(500, {"error": "internal error"})

    def do_POST(self):
        try:
            if not self._host_ok():
                return self._send(403, {"error": "forbidden host"})
            route = self.path.split("?")[0]
            if route not in POST_ROUTES:
                return self._send(404, {"error": "not found", "routes": ROUTES})
            params = self._read_body_params()
            if params is None:
                return  # a 400/413 error response was already sent
            if route == "/compare":
                tsm = _clamp(params.get("target_support_m", 100.0), 1.0, 100000.0, 100.0)
                nb = int(_clamp(params.get("n_boot", 0), 0, MAX_BOOT, 0))
                pkg = study.run_study(target_support_m=tsm, n_boot=nb)
                return self._send(200, {"params": {"target_support_m": tsm, "n_boot": nb},
                                        "result": pkg})
            if route == "/validate":
                return self._post_validate(params)
            if route == "/batch":
                return self._post_batch(params)
            return self._post_report(params)
        except Exception:
            return self._send(500, {"error": "internal error"})

    def _read_body_params(self):
        """Read and validate a JSON-object request body under the security rules
        shared by every POST route (64 KiB body cap + JSON content validation).

        Returns the parsed dict (``{}`` for an empty body) on success, or ``None``
        after having already sent the appropriate error: 400 for an invalid
        Content-Length / malformed JSON / non-object body, 413 if the body exceeds
        MAX_BODY. Mirrors the original /compare body handling verbatim so every
        existing security behaviour is preserved for the new routes too.
        """
        raw_len = self.headers.get("Content-Length")
        try:
            n = int(raw_len) if raw_len is not None else 0
        except ValueError:
            self._send(400, {"error": "invalid Content-Length"})
            return None
        if n < 0:
            self._send(400, {"error": "invalid Content-Length"})
            return None
        if n > MAX_BODY:
            self._send(413, {"error": f"body too large (max {MAX_BODY} bytes)"})
            return None
        try:
            params = json.loads(self.rfile.read(n) or b"{}") if n else {}
        except Exception:
            self._send(400, {"error": "invalid JSON body"})
            return None
        if not isinstance(params, dict):
            self._send(400, {"error": "body must be a JSON object"})
            return None
        return params

    def _bodies(self):
        """Supported reference bodies + the data-source registry, from the catalog.

        `bodies` is the set of reference bodies the catalog can serve (mars, moon,
        earth, ...); `sources` is the compact per-product registry.
        """
        sources = []
        for sid in catalog.all_ids():
            s = catalog.get(sid)
            sources.append({"id": s["id"], "body": s["body"], "product": s["product"],
                            "native_resolution_m": s["native_resolution_m"],
                            "key_required": s["key_required"]})
        bodies = sorted({s["body"] for s in sources})
        return {"bodies": bodies, "sources": sources}

    def _post_validate(self, params):
        """Run the scientific-correctness validation suite; return a modest
        summary (counts + per-check pass/fail + the stable outcome hash), omitting
        the big per-check metric detail to keep the response small."""
        rep = validation.run_validation()
        return self._send(200, {
            "passed": rep["passed"], "failed": rep["failed"],
            "all_passed": rep["all_passed"], "package_hash": rep["package_hash"],
            "checks": [{"name": c["name"], "passed": c["passed"]}
                       for c in rep.get("checks", [])],
        })

    def _post_batch(self, params):
        """Small, fast synthetic cross-reference batch (two Mars references vs a
        few Earth candidates). Honours an optional {"decision_modes": [...]};
        unknown modes are dropped and the default ("core",) keeps it quick.
        Returns the compact batch subset."""
        allowed = ("core", "extended", "geomorphic")
        requested = params.get("decision_modes")
        modes = tuple(m for m in requested if m in allowed) \
            if isinstance(requested, list) else ()
        if not modes:
            modes = ("core",)
        units, references, candidates = _synthetic_batch()
        rep = batch.run_batch(units, references, candidates, 30.0, decision_modes=modes)
        subset = {k: rep[k] for k in ("references", "candidates", "consensus_shortlist",
                                      "robust_ordering", "per_candidate", "package_hash")}
        subset["decision_modes"] = list(rep.get("decision_modes", modes))
        return self._send(200, subset)

    def _post_report(self, params):
        """Run the canonical synthetic study (same validated params as /compare)
        and render it as a publication-grade Markdown report. report is
        lazy-imported here so simply importing the API stays light."""
        from . import report
        tsm = _clamp(params.get("target_support_m", 100.0), 1.0, 100000.0, 100.0)
        nb = int(_clamp(params.get("n_boot", 0), 0, MAX_BOOT, 0))
        pkg = study.run_study(target_support_m=tsm, n_boot=nb)
        return self._send(200, {"markdown": report.study_report_md(pkg),
                                "package_hash": pkg.get("package_hash"),
                                "params": {"target_support_m": tsm, "n_boot": nb}})


def make_server(host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), Handler)


def main(argv=None):
    ap = argparse.ArgumentParser(description="TerraTrace stdlib HTTP API")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--allow-remote", action="store_true",
                    help="permit binding a non-loopback host (adds no auth; use behind a proxy)")
    args = ap.parse_args(argv)
    if args.host not in LOOPBACK and not args.host.startswith("127.") and not args.allow_remote:
        raise SystemExit("Refusing to bind a non-loopback host without --allow-remote "
                         "(the server is unauthenticated). Put auth/rate-limiting in front first.")
    srv = make_server(args.host, args.port)
    print(f"TerraTrace API -> http://{args.host}:{args.port}")
    print("UNAUTHENTICATED; loopback-only Host allowlist. Add auth before exposing.")
    print("routes:", ", ".join(ROUTES))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
