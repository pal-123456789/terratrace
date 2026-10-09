"""Minimal, dependency-free HTTP API for TerraTrace.

Exposes the engine over HTTP using only the Python standard library (no Flask/
FastAPI needed), so it runs anywhere Python does. Endpoints:

    GET  /health            -> liveness + version
    GET  /study             -> the canonical synthetic study package (JSON)
    POST /compare           -> run a synthetic study with validated parameters
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

from . import __version__, study

MAX_BOOT = 2000
ROUTES = ["GET /health", "GET /study", "POST /compare"]


def _clamp(value, lo, hi, default):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


class Handler(BaseHTTPRequestHandler):
    server_version = "TerraTrace/" + __version__

    def _send(self, code, obj):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(body)

    def log_message(self, *args):
        pass  # quiet

    def do_GET(self):
        if self.path.split("?")[0] == "/health":
            return self._send(200, {"status": "ok", "service": "terratrace",
                                    "version": __version__, "routes": ROUTES})
        if self.path.split("?")[0] == "/study":
            return self._send(200, study.run_study())
        return self._send(404, {"error": "not found", "routes": ROUTES})

    def do_POST(self):
        if self.path.split("?")[0] != "/compare":
            return self._send(404, {"error": "not found", "routes": ROUTES})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            params = json.loads(self.rfile.read(n) or b"{}") if n else {}
        except Exception as exc:
            return self._send(400, {"error": "invalid JSON body", "detail": str(exc)})
        if not isinstance(params, dict):
            return self._send(400, {"error": "body must be a JSON object"})
        tsm = _clamp(params.get("target_support_m", 100.0), 1.0, 100000.0, 100.0)
        nb = int(_clamp(params.get("n_boot", 0), 0, MAX_BOOT, 0))
        pkg = study.run_study(target_support_m=tsm, n_boot=nb)
        return self._send(200, {"params": {"target_support_m": tsm, "n_boot": nb}, "result": pkg})


def make_server(host="127.0.0.1", port=8000):
    return ThreadingHTTPServer((host, port), Handler)


def main(argv=None):
    ap = argparse.ArgumentParser(description="TerraTrace stdlib HTTP API")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args(argv)
    srv = make_server(args.host, args.port)
    print(f"TerraTrace API -> http://{args.host}:{args.port}")
    print("UNAUTHENTICATED, localhost-only by default; add auth before exposing.")
    print("routes:", ", ".join(ROUTES))
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        srv.shutdown()


if __name__ == "__main__":
    main()
