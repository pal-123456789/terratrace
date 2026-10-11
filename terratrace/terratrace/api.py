"""Minimal, dependency-free HTTP API for TerraTrace.

Exposes the engine over HTTP using only the Python standard library (no Flask/
FastAPI needed), so it runs anywhere Python does. Endpoints:

    GET  /health            -> liveness + version
    GET  /study             -> the canonical synthetic study package (JSON)
    GET  /bodies            -> supported reference bodies + data-source registry
    GET  /references        -> upstream data-source citation / credits catalogue
    POST /compare           -> run a synthetic study with validated parameters
                               body: {"target_support_m": float, "n_boot": int,
                                      "significance": bool, "n_perm": int}
                               (significance opts in to the permutation block)
    POST /validate          -> run the scientific-correctness validation suite
    POST /batch             -> a small synthetic cross-reference batch study
                               body: {"decision_modes": ["core", ...]}
    POST /report            -> run_study + render a publication-grade Markdown report
                               body: {"target_support_m": float, "n_boot": int}
    POST /dossier           -> run_study + per-candidate decision briefs (JSON)
                               body: {"target_support_m": float, "n_boot": int,
                                      "unit": "<id>"}  # optional: just that one unit
    POST /report.html       -> run_study + render the report as a standalone HTML
                               document (Content-Type text/html, NOT JSON)
                               body: {"target_support_m": float, "n_boot": int}
    POST /sensitivity       -> decision-lens robustness ablation over a small
                               synthetic clear-winner scene (no array upload)
                               body: {"target_support_m": float}  # optional
    POST /classify          -> terrain-type classifier run on three synthetic
                               grids of increasing roughness (no array upload)
    POST /confidence        -> non-composite decision confidence for a POSTed
                               study package (the request body IS the study
                               package JSON); returns the verdict + per-signal
                               evidence + caveats as JSON
    POST /bank              -> full geomorphometric descriptor bank for a POSTed
                               tile
                               body: {"z": [[...]], "dx": float}  # dx optional
                               returns descriptors.descriptor_bank(z, dx) as JSON
    POST /transect          -> transect signature along p0->p1 of a POSTed tile
                               body: {"z": [[...]], "p0": [r,c], "p1": [r,c],
                                      "dx": float}  # dx optional
                               returns transect.transect_signature(...) as JSON

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

import numpy as np

from . import __version__, study, catalog, validation, batch, synthetic

MAX_BOOT = 500             # interactive responsiveness cap for the HTTP endpoint
                           # (~7 s worst case); the library accepts any n_boot offline.
MAX_PERM = 2000            # interactive cap on the significance permutation count
                           # (mirrors MAX_BOOT); the library accepts any n_perm offline.
MAX_BODY = 1 << 16          # 64 KiB cap on request bodies
LOOPBACK = {"127.0.0.1", "localhost", "::1", "[::1]"}
ROUTES = ["GET /health", "GET /study", "GET /bodies", "GET /references",
          "POST /compare", "POST /validate", "POST /batch", "POST /report",
          "POST /dossier", "POST /report.html", "POST /sensitivity", "POST /classify",
          "POST /confidence", "POST /bank", "POST /transect"]
POST_ROUTES = ("/compare", "/validate", "/batch", "/report", "/dossier",
               "/report.html", "/sensitivity", "/classify", "/confidence",
               "/bank", "/transect")


def _clamp(value, lo, hi, default):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    return max(lo, min(hi, v))


def _study_package(target_support_m, n_boot, significance, n_perm):
    """Run the canonical synthetic study, optionally attaching the opt-in
    permutation-significance block.

    With ``significance`` off this is exactly ``study.run_study(...)`` so the
    existing /compare bytes are unchanged. With it on, the SAME synthetic
    units/rights (mirroring run_study) are routed through ``study.compare_units``
    so the significance block can be requested (run_study itself takes no
    significance args). ``significance=False`` attaches nothing, so the two paths
    agree when the flag is off. Distribution-shape resampling statistics only."""
    if not significance:
        return study.run_study(target_support_m=target_support_m, n_boot=n_boot)
    raw = {"mars_reference": study._unit_grid("reference"),
           "earth_close": study._unit_grid("earth_close"),
           "earth_far": study._unit_grid("earth_far"),
           "earth_blocked": study._unit_grid("earth_blocked")}
    rights = {"mars_reference": "verified_allowed", "earth_close": "verified_allowed",
              "earth_far": "verified_allowed", "earth_blocked": "unknown"}
    return study.compare_units(raw, rights, 25.0, target_support_m=target_support_m,
                               min_valid=0.5, source_label="synthetic", n_boot=n_boot,
                               significance=True, n_perm=n_perm)


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


_SENS_NATIVE_M = 10.0       # native posting (m) of the synthetic sensitivity scene


def _sensitivity_scene(shape=(48, 48)):
    """Small deterministic clear-winner scene for the decision-sensitivity demo:
    a reference, a 'near' candidate statistically like it, and a much rougher
    'far' candidate -- an unambiguous, reproducible winner, mirroring
    test_sensitivity's _clear_winner_scene (and run_study's _unit_grid) at a tiny
    size so the ablation stays fast. Returns (raw_units, rights)."""
    base = synthetic.plane(shape, slope_x=0.02, dx=_SENS_NATIVE_M)
    raw = {
        "ref": base + synthetic.rough_field(shape, 0.8, seed=1),
        "near": base + synthetic.rough_field(shape, 0.9, seed=2),
        "far": base + synthetic.rough_field(shape, 4.0, seed=3),
    }
    rights = {k: "verified_allowed" for k in raw}
    return raw, rights


def _classify_scenes(shape=(48, 48)):
    """Three deterministic synthetic grids of increasing roughness for the
    terrain-type classifier demo: a smooth near-flat plane, a 'rolling' reference
    dome, and a rough white-noise field. These mirror the proven
    test_terrain_classify fixtures (reused via synthetic.*), so the classifier is
    exercised across its vocabulary without needing an uploaded array.
    Returns {label: 2-D elevation grid}."""
    return {
        "reference": synthetic.gaussian_hill(shape, amplitude=10.0, sigma=12.0),
        "smooth": synthetic.plane(shape, slope_x=0.001, slope_y=0.0005),
        "rough": (synthetic.plane(shape, slope_x=0.2, slope_y=0.1)
                  + synthetic.rough_field(shape, amplitude=5.0, seed=11)),
    }


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

    def _send_html(self, code, html_str):
        """Send `html_str` as an HTML response (text/html; charset=utf-8), not
        JSON. A sibling of `_send` that leaves `_send` untouched, so routes that
        return a rendered document (e.g. /report.html) can bypass JSON encoding
        while keeping the same Content-Length / HEAD handling."""
        body = (html_str or "").encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
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
            if route == "/references":
                # Upstream data-source citation / credits catalogue (a GET like
                # /bodies). references is lazy-imported so importing the API stays light.
                from . import references
                return self._send(200, {"references": references.references_for()})
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
                sig = bool(params.get("significance", False))
                npm = int(_clamp(params.get("n_perm", 1000), 1, MAX_PERM, 1000))
                pkg = _study_package(tsm, nb, sig, npm)
                return self._send(200, {"params": {"target_support_m": tsm, "n_boot": nb,
                                                    "significance": sig, "n_perm": npm},
                                        "result": pkg})
            if route == "/validate":
                return self._post_validate(params)
            if route == "/batch":
                return self._post_batch(params)
            if route == "/dossier":
                return self._post_dossier(params)
            if route == "/report.html":
                return self._post_report_html(params)
            if route == "/sensitivity":
                return self._post_sensitivity(params)
            if route == "/classify":
                return self._post_classify(params)
            if route == "/confidence":
                return self._post_confidence(params)
            if route == "/bank":
                return self._post_bank(params)
            if route == "/transect":
                return self._post_transect(params)
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

    def _post_dossier(self, params):
        """Run the canonical synthetic study (same validated params as /compare)
        and return per-candidate decision briefs. With no "unit" key, returns
        dossier.all_dossiers(package): a {unit_id: brief} dict for every unit in
        the package. With {"unit": "<id>"}, returns dossier.candidate_dossier for
        just that unit, answering 400 with a JSON error (never crashing) when the
        unit is unknown. dossier is lazy-imported so importing the API stays light.
        """
        from . import dossier
        tsm = _clamp(params.get("target_support_m", 100.0), 1.0, 100000.0, 100.0)
        nb = int(_clamp(params.get("n_boot", 0), 0, MAX_BOOT, 0))
        pkg = study.run_study(target_support_m=tsm, n_boot=nb)
        unit = params.get("unit")
        if unit is not None:
            try:
                brief = dossier.candidate_dossier(pkg, unit)
            except KeyError:
                return self._send(400, {"error": f"unknown unit {unit!r}"})
            return self._send(200, brief)
        return self._send(200, dossier.all_dossiers(pkg))

    def _post_report_html(self, params):
        """Run the canonical synthetic study (same validated params as /compare)
        and render it as a complete, self-contained HTML document, returned as an
        HTML response (text/html; charset=utf-8), NOT JSON. report_html is
        lazy-imported here so simply importing the API stays light."""
        from . import report_html
        tsm = _clamp(params.get("target_support_m", 100.0), 1.0, 100000.0, 100.0)
        nb = int(_clamp(params.get("n_boot", 0), 0, MAX_BOOT, 0))
        pkg = study.run_study(target_support_m=tsm, n_boot=nb)
        return self._send_html(200, report_html.study_report_html(pkg))

    def _post_sensitivity(self, params):
        """Decision-lens robustness ablation over a small deterministic
        clear-winner scene (reference + a near and a far candidate; see
        _sensitivity_scene). Re-runs the morphology screen under every decision
        lens at a fixed common support and reports whether the recommendation
        survives. Honours an optional {"target_support_m"}, clamped exactly like
        /compare (default = the scene's native posting so the empty-body demo
        shows the clear winner). sensitivity is lazy-imported so importing the API
        stays light. This is a robustness diagnostic, not a new scientific claim."""
        from . import sensitivity
        tsm = _clamp(params.get("target_support_m", _SENS_NATIVE_M), 1.0, 100000.0, _SENS_NATIVE_M)
        raw, rights = _sensitivity_scene()
        rep = sensitivity.lens_ablation(raw, rights, native_posting_m=_SENS_NATIVE_M,
                                        reference_id="ref", target_support_m=tsm)
        return self._send(200, {"recommendation_stable": rep["recommendation_stable"],
                                "recommended_units": rep["recommended_units"],
                                "per_lens": rep["per_lens"]})

    def _post_classify(self, params):
        """Run the transparent, rule-based terrain-type classifier on three
        deterministic synthetic grids of increasing roughness (see
        _classify_scenes), demonstrating the classifier without an uploaded array.
        Returns {"classes": {label: type}} with the chosen morphology type per
        grid. No request params are required; the body is still read/validated via
        the shared POST path. terrain_classify is lazy-imported so importing the
        API stays light. The type is a descriptive map-scale morphology label, not
        a geological, hazard, or traversability claim."""
        from . import terrain_classify
        classes = {label: terrain_classify.classify(grid)["type"]
                   for label, grid in _classify_scenes().items()}
        return self._send(200, {"classes": classes})

    def _post_confidence(self, params):
        """Compute the non-composite decision confidence for a POSTed study
        package. The request body IS the study package JSON (the same shape /study
        and /compare's ``result`` return); this returns
        confidence.decision_confidence(package) as JSON -- the verdict, the three
        independent robustness signals, and the caveats. The package is read
        READ-ONLY and never mutated. confidence is lazy-imported so importing the
        API stays light.

        The shared POST security rules apply unchanged: the 64 KiB body cap, the
        JSON-object validation, and the loopback Host allowlist. A full study
        package WITH inline previews can exceed 64 KiB and will be rejected with
        413; post the decision-relevant keys (result_state, recommended_unit,
        bootstrap, significance) for such cases. This restates robustness evidence
        already in the package; it is not a new scientific or mission claim."""
        from . import confidence
        return self._send(200, confidence.decision_confidence(params))

    def _grid_or_400(self, params):
        """Coerce ``params["z"]`` to a non-empty 2-D float ndarray, or send the
        matching 400 and return ``None``. Mirrors the engine's own
        ``np.asarray(z, dtype=float)`` so a ragged / non-numeric / wrong-rank
        array is rejected cleanly (400) instead of surfacing as a 500."""
        z = params.get("z")
        if z is None:
            self._send(400, {"error": "missing 'z' (a 2-D array of elevations)"})
            return None
        try:
            arr = np.asarray(z, dtype=float)
        except (TypeError, ValueError):
            self._send(400, {"error": "'z' must be a numeric 2-D array"})
            return None
        if arr.ndim != 2 or min(arr.shape) < 1:
            self._send(400, {"error": "'z' must be a non-empty 2-D array"})
            return None
        return arr

    @staticmethod
    def _point(value):
        """Coerce a ``[row, col]`` request value to a ``(row, col)`` float tuple,
        or ``None`` if it is not a 2-element numeric sequence."""
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            return None
        try:
            return (float(value[0]), float(value[1]))
        except (TypeError, ValueError):
            return None

    def _post_bank(self, params):
        """Full geomorphometric descriptor bank for a POSTed elevation tile. The
        body carries a 2-D array ``"z"`` and an optional ``"dx"`` (pixel size in
        metres, clamped like the other numeric params); returns
        descriptors.descriptor_bank(z, dx) -- a flat JSON bag of map-scale
        morphology descriptors. The shared POST security rules apply unchanged
        (64 KiB body cap, loopback Host allowlist, JSON-object validation); a
        malformed/non-numeric/wrong-rank ``z`` is a 400 and an oversize body a 413.
        descriptors is lazy-imported so importing the API stays light. READ-ONLY
        analysis surface consulted by no decision; no traversability / mechanical /
        mission claim is implied."""
        arr = self._grid_or_400(params)
        if arr is None:
            return  # a 400 was already sent
        dx = _clamp(params.get("dx", 1.0), 1e-6, 1e6, 1.0)
        from . import descriptors
        return self._send(200, descriptors.descriptor_bank(arr, dx))

    def _post_transect(self, params):
        """Transect signature along ``p0 -> p1`` of a POSTed elevation tile. The
        body carries a 2-D array ``"z"``, two ``[row, col]`` pixel endpoints
        ``"p0"`` / ``"p1"``, and an optional ``"dx"`` (clamped like the other
        numeric params); returns transect.transect_signature(z, p0, p1, dx) -- the
        flat scalar summary (length / relief / max & mean slope / elevation gain).
        The shared POST security rules apply unchanged (64 KiB body cap, loopback
        Host allowlist, JSON-object validation); a bad ``z`` or a non-2-element
        ``p0`` / ``p1`` is a 400 and an oversize body a 413. transect is
        lazy-imported so importing the API stays light. Purely geometric map-scale
        morphology -- see the transect module's claim firewall."""
        arr = self._grid_or_400(params)
        if arr is None:
            return  # a 400 was already sent
        p0 = self._point(params.get("p0"))
        p1 = self._point(params.get("p1"))
        if p0 is None or p1 is None:
            return self._send(400, {"error": "'p0' and 'p1' must each be [row, col]"})
        dx = _clamp(params.get("dx", 1.0), 1e-6, 1e6, 1.0)
        from . import transect
        return self._send(200, transect.transect_signature(arr, p0, p1, dx))


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
