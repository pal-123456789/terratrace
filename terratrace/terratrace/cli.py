"""Unified TerraTrace command-line dispatcher.

Usage: ``python -m terratrace.cli <command> [options]``

Commands:
  study      run the synthetic reference study and emit a study package (default)
  validate   run the scientific-correctness validation suite
  benchmark  run the reproducibility + scaling benchmark
  report     render a markdown report from a study JSON
  report-html render a self-contained HTML report from a study JSON
  dossier    print a per-candidate site dossier from a study JSON
  references print the data-sources citation / credits bundle (Markdown)
  sensitivity run a decision-lens robustness ablation on a synthetic scene
  classify   label synthetic terrains by map-scale morphology type
  confidence print the non-composite decision confidence for a study JSON
  bank       compute the full geomorphometric descriptor bank for one tile (JSON)
  transect   emit a transect signature (and optional profile) along a line (JSON)
  version    print the TerraTrace version and schema version

Backward compatibility: the original CLI ran a study directly with options like
``--out``. When the first token is not a known command (empty, or starting with
"-"), the whole invocation is routed to the implicit ``study`` command, so
existing calls such as ``python -m terratrace.cli --out artifacts`` and the
tests that drive them keep working unchanged.

Each command lazily imports its engine module *inside* its handler, so a module
with an optional/heavy dependency (or one supplied by a separate build, like
``report``) never breaks ``import terratrace.cli`` or the other commands.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

from . import __version__ as _PACKAGE_VERSION

# Mirrors study.compare_units' package schema_version; a constant keeps the
# `version` command instant (no study run, no heavy import). This is the
# BUNDLE-SCHEMA version -- a different, slower-moving number than the package
# version, which lives once in ``terratrace.__version__``.
_SCHEMA_VERSION = "0.1.0"


def _cmd_study(argv):
    """Legacy behaviour: run the synthetic study and write the artifact set.

    ``--significance`` opts in to the GATED resampling-significance block on the
    recommendation (one-sided permutation closeness test vs the runner-up);
    ``--n-perm`` sets its permutation count. Both are forwarded into the study
    call. After the study runs, the non-composite decision confidence (verdict +
    one-line rationale) is printed. Significance is off by default, so the legacy
    artifact bytes are unchanged unless the flag is given."""
    ap = argparse.ArgumentParser(
        prog="terratrace study",
        description="Run the synthetic reference study and emit a study package.")
    ap.add_argument("--out", default="artifacts", help="output directory")
    ap.add_argument("--target-support-m", type=float, default=100.0)
    ap.add_argument("--native-posting-m", type=float, default=25.0)
    ap.add_argument("--significance", action="store_true",
                    help="attach the opt-in permutation-significance block on the recommendation")
    ap.add_argument("--n-perm", type=int, default=1000,
                    help="permutation count for --significance (default 1000)")
    args = ap.parse_args(argv)
    if args.target_support_m <= 0 or args.native_posting_m <= 0:
        raise SystemExit("--target-support-m and --native-posting-m must be positive")
    if args.n_perm <= 0:
        raise SystemExit("--n-perm must be positive")

    from .provenance import sha256_json
    from .confidence import decision_confidence

    pkg = _run_synthetic_study(args.target_support_m, args.native_posting_m,
                               args.significance, args.n_perm)

    os.makedirs(args.out, exist_ok=True)
    files = {
        "study.json": pkg,
        "profile.json": pkg["profile"],
        "transfer-gap-ledger.json": pkg["transfer_gap_ledger"],
        "draft-protocol.json": pkg["draft_protocol"],
        "evidence-graph.json": pkg["evidence_graph"],
    }
    checksums = {}
    for name, obj in files.items():
        path = os.path.join(args.out, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(obj, fh, indent=2, sort_keys=True)
        checksums[name] = sha256_json(obj)

    manifest = {
        "release": f"terratrace-v{_PACKAGE_VERSION}",
        "result_state": pkg["result_state"],
        "recommended_unit": pkg["recommended_unit"],
        "package_hash": pkg["package_hash"],
        "artifacts": checksums,
        "claim_maturity": pkg["profile"]["claim_maturity"],
    }
    with open(os.path.join(args.out, "manifest.json"), "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    with open(os.path.join(args.out, "checksums.txt"), "w", encoding="utf-8") as fh:
        for name, digest in sorted(checksums.items()):
            fh.write(f"{digest}  {name}\n")

    conf = decision_confidence(pkg)
    print(f"result_state       = {pkg['result_state']}")
    print(f"recommended_unit   = {pkg['recommended_unit']}")
    print(f"package_hash       = {pkg['package_hash'][:16]}...")
    print(f"decision_confidence= {conf['verdict']}")
    print(f"confidence_rationale = {conf['rationale']}")
    print(f"artifacts written  -> {args.out}")
    return 0


def _run_synthetic_study(target_support_m, native_posting_m, significance, n_perm):
    """Produce the canonical synthetic study package.

    With significance OFF this is exactly ``study.run_study(...)`` so the legacy
    artifact bytes are byte-for-byte preserved. With significance ON, the SAME
    synthetic units/rights are routed through ``study.compare_units`` so the
    opt-in permutation-significance block can be requested (``run_study`` itself
    takes no significance arguments). ``significance=False`` attaches nothing, so
    the two paths produce identical packages when the flag is off.
    """
    from .study import run_study
    if not significance:
        return run_study(target_support_m=target_support_m,
                         native_posting_m=native_posting_m)
    from .study import compare_units, _unit_grid
    raw = {"mars_reference": _unit_grid("reference"),
           "earth_close": _unit_grid("earth_close"),
           "earth_far": _unit_grid("earth_far"),
           "earth_blocked": _unit_grid("earth_blocked")}
    rights = {"mars_reference": "verified_allowed", "earth_close": "verified_allowed",
              "earth_far": "verified_allowed", "earth_blocked": "unknown"}
    return compare_units(raw, rights, native_posting_m,
                         target_support_m=target_support_m, min_valid=0.5,
                         source_label="synthetic", significance=True, n_perm=n_perm)


def _cmd_validate(argv):
    """Run the scientific-correctness suite; exit 0 iff every check passes."""
    ap = argparse.ArgumentParser(
        prog="terratrace validate",
        description="Run the scientific-correctness validation suite.")
    ap.parse_args(argv)
    from terratrace import validation
    rep = validation.run_validation()
    print(f"validation: {rep['passed']} passed, {rep['failed']} failed, "
          f"all_passed={rep['all_passed']}")
    return 0 if rep["all_passed"] else 1


def _cmd_benchmark(argv):
    """Run the invariant + scaling benchmark at small sizes; 0 iff all pass."""
    ap = argparse.ArgumentParser(
        prog="terratrace benchmark",
        description="Run the reproducibility + scaling benchmark (small sizes).")
    ap.parse_args(argv)
    from terratrace import benchmark
    rep = benchmark.run_benchmark(sizes=(32, 64), repeats=1)
    print(f"benchmark: {rep['passed']} passed, {rep['failed']} failed, "
          f"all_passed={rep['all_passed']}")
    scaling = rep.get("scaling", [])
    if scaling:
        line = "  ".join(f"{r['size']}x{r['size']}={r['seconds']}s" for r in scaling)
        print(f"scaling: {line}")
    return 0 if rep["all_passed"] else 1


def _cmd_report(argv):
    """Render a markdown report from a study JSON via terratrace.report."""
    ap = argparse.ArgumentParser(
        prog="terratrace report",
        description="Render a markdown report from a study JSON package.")
    ap.add_argument("--study", default=os.path.join("artifacts", "study.json"),
                    help="input study JSON (default: artifacts/study.json)")
    ap.add_argument("--out", default=os.path.join("artifacts", "study_report.md"),
                    help="output markdown path (default: artifacts/study_report.md)")
    args = ap.parse_args(argv)
    # Lazy import: report.py may be provided by a separate build, so importing
    # it here keeps `import terratrace.cli` and the other commands working even
    # when it is absent.
    from terratrace import report
    with open(args.study, "r", encoding="utf-8") as fh:
        study = json.load(fh)
    md = report.study_report_md(study)
    try:
        report.write_report(md, args.out)        # (content, path)
    except TypeError:
        report.write_report(args.out, md)        # tolerate (path, content)
    print(args.out)
    return 0


def _cmd_report_html(argv):
    """Render a self-contained HTML report from a study JSON via report_html."""
    ap = argparse.ArgumentParser(
        prog="terratrace report-html",
        description="Render a self-contained HTML report from a study JSON package.")
    ap.add_argument("--study", default=os.path.join("artifacts", "study.json"),
                    help="input study JSON (default: artifacts/study.json)")
    ap.add_argument("--out", default=os.path.join("artifacts", "study_report.html"),
                    help="output HTML path (default: artifacts/study_report.html)")
    args = ap.parse_args(argv)
    # Lazy import: report_html may be supplied by a separate build and is still
    # being extended, so importing it here keeps `import terratrace.cli` and the
    # other commands working even if it is absent.
    from terratrace import report_html
    with open(args.study, "r", encoding="utf-8") as fh:
        package = json.load(fh)
    doc = report_html.study_report_html(package)
    report_html.write_html(doc, args.out)
    print(args.out)
    return 0


def _cmd_dossier(argv):
    """Print a per-candidate site dossier (one unit) or a one-line summary of all."""
    ap = argparse.ArgumentParser(
        prog="terratrace dossier",
        description="Print a per-candidate site dossier from a study JSON package.")
    ap.add_argument("--study", default=os.path.join("artifacts", "study.json"),
                    help="input study JSON (default: artifacts/study.json)")
    ap.add_argument("--unit", default=None,
                    help="candidate unit id; omit for a one-line summary of every unit")
    args = ap.parse_args(argv)
    # Lazy import keeps `import terratrace.cli` cheap and dependency-free.
    from terratrace import dossier
    try:
        with open(args.study, "r", encoding="utf-8") as fh:
            package = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            f"terratrace dossier: cannot read study file {args.study!r}: {exc}\n")
        return 2
    if args.unit is not None:
        try:
            md = dossier.dossier_md(package, args.unit)
        except KeyError:
            sys.stderr.write(
                f"terratrace dossier: unknown unit {args.unit!r} in study "
                f"{args.study!r}\n")
            return 2
        print(md, end="")
        return 0
    briefs = dossier.all_dossiers(package)
    if not briefs:
        print("(no units in study package)")
        return 0
    for uid in sorted(briefs):
        d = briefs[uid]
        print(f"{uid}\teligible={d['eligible']}\t"
              f"recommended={d['is_recommended']}")
    return 0


def _cmd_references(argv):
    """Print the data-sources citation / credits bundle (Markdown) to stdout.

    With ``--out PATH`` the Markdown is written to that file instead (and the
    path is echoed), mirroring the report/report-html commands.
    """
    ap = argparse.ArgumentParser(
        prog="terratrace references",
        description="Print the data-sources citation / credits bundle (Markdown).")
    ap.add_argument("--out", default=None,
                    help="write the Markdown to this file instead of stdout")
    args = ap.parse_args(argv)
    # Lazy import keeps `import terratrace.cli` cheap and dependency-free.
    from terratrace import references
    md = references.references_md()
    if args.out:
        with open(args.out, "w", encoding="utf-8") as fh:
            fh.write(md)
        print(args.out)
    else:
        sys.stdout.write(md)
    return 0


def _cmd_sensitivity(argv):
    """Run a decision-lens robustness ablation on a synthetic clear-winner scene.

    Builds a small deterministic reference/near/far scene (~48x48, as in
    test_sensitivity: a gently-sloped rough plane, a statistically-similar
    ``near``, and a much rougher ``far``), runs :func:`sensitivity.lens_ablation`
    across the decision lenses, and prints a one-line verdict. This is a
    robustness diagnostic over the map-scale morphology screen, not a new claim.
    """
    ap = argparse.ArgumentParser(
        prog="terratrace sensitivity",
        description="Run a decision-lens robustness ablation on a synthetic scene.")
    ap.parse_args(argv)
    # Lazy import keeps `import terratrace.cli` cheap and dependency-free.
    from terratrace import sensitivity, synthetic
    n, L = 48, 10.0
    base = synthetic.plane((n, n), slope_x=0.02, dx=L)
    raw = {
        "ref":  base + synthetic.rough_field((n, n), 0.8, seed=1),
        "near": base + synthetic.rough_field((n, n), 0.9, seed=2),
        "far":  base + synthetic.rough_field((n, n), 4.0, seed=3),
    }
    rights = {k: "verified_allowed" for k in raw}
    rep = sensitivity.lens_ablation(raw, rights, native_posting_m=L,
                                    reference_id="ref", target_support_m=L)
    states = " ".join(f"{lens}={entry['result_state']}"
                      for lens, entry in rep["per_lens"].items())
    print(f"recommendation_stable={rep['recommendation_stable']} "
          f"recommended_units={rep['recommended_units']} "
          f"lenses: {states}")
    return 0


def _cmd_classify(argv):
    """Label three synthetic terrains by their map-scale morphology type.

    Builds the three study-style synthetic terrains offline -- the study's Mars
    reference grid, a smooth gaussian dome, and a rough noisy plane -- runs the
    transparent rule-based :func:`terrain_classify.classify` on each, and prints
    ``label: type (confidence)``. The type is a DESCRIPTIVE morphology label
    only (no geologic, hazard, or rover-traversability claim).
    """
    ap = argparse.ArgumentParser(
        prog="terratrace classify",
        description="Label synthetic terrains by map-scale morphology type.")
    ap.parse_args(argv)
    # Lazy imports keep `import terratrace.cli` cheap and dependency-free.
    from terratrace import terrain_classify, synthetic, study
    shape = (56, 56)
    terrains = {
        "reference": study._unit_grid("reference", shape),
        "smooth": synthetic.gaussian_hill(shape, amplitude=10.0, sigma=12.0),
        "rough": (synthetic.plane(shape, slope_x=0.2, slope_y=0.1)
                  + synthetic.rough_field(shape, amplitude=5.0, seed=11)),
    }
    for label in ("reference", "smooth", "rough"):
        r = terrain_classify.classify(terrains[label])
        print(f"{label}: {r['type']} ({r['confidence']:.2f})")
    return 0


def _cmd_confidence(argv):
    """Print the non-composite decision confidence for a study JSON package.

    Loads a study package JSON (same ``--study`` input convention as the report /
    dossier commands) and prints :func:`terratrace.confidence.decision_confidence`
    -- the verdict, each independent signal (evaluated flag + detail), and the
    caveats -- as human-readable text, or as a JSON object with ``--json``. This
    restates robustness evidence already in the package; it is NOT a new claim and
    emits no composite score.
    """
    ap = argparse.ArgumentParser(
        prog="terratrace confidence",
        description="Print the non-composite decision confidence for a study JSON package.")
    ap.add_argument("--study", default=os.path.join("artifacts", "study.json"),
                    help="input study JSON (default: artifacts/study.json)")
    ap.add_argument("--json", action="store_true",
                    help="emit the full confidence dict as JSON instead of text")
    args = ap.parse_args(argv)
    # Lazy import keeps `import terratrace.cli` cheap and dependency-free.
    from terratrace import confidence
    try:
        with open(args.study, "r", encoding="utf-8") as fh:
            package = json.load(fh)
    except OSError as exc:
        sys.stderr.write(
            f"terratrace confidence: cannot read study file {args.study!r}: {exc}\n")
        return 2
    out = confidence.decision_confidence(package)
    if args.json:
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    print(f"verdict:          {out['verdict']}")
    print(f"result_state:     {out['state']}")
    print(f"recommended_unit: {out['recommended_unit']}")
    print(f"rationale:        {out['rationale']}")
    print("signals:")
    for name in confidence.SIGNAL_NAMES:
        s = out["signals"][name]
        print(f"  {name}: evaluated={s['evaluated']}  {s['detail']}")
    if out["caveats"]:
        print("caveats:")
        for c in out["caveats"]:
            print(f"  - {c}")
    return 0


def _synthetic_tile(shape=(48, 48)):
    """Return a deterministic, well-conditioned synthetic elevation tile.

    A gently tilted plane + a central gaussian dome + seeded roughness, so that
    slope, relief, curvature, texture and fabric descriptors are all
    non-degenerate -- mirroring the synthetic scenes used by the classify /
    sensitivity subcommands. The tile is generated in unit pixel space; the real
    pixel size (``dx``) is applied later by the descriptor / transect call, so
    there is no double-counting of ``dx``.
    """
    from terratrace import synthetic
    base = synthetic.plane(shape, slope_x=0.03, slope_y=0.01)
    dome = synthetic.gaussian_hill(shape, amplitude=12.0, sigma=10.0)
    rough = synthetic.rough_field(shape, amplitude=1.5, seed=7)
    return base + dome + rough


def _load_tile(path):
    """Load a 2-D elevation array from ``path``.

    A NumPy ``.npy`` file (loaded with ``allow_pickle=False``, the safe default),
    a ``.json`` file holding a 2-D array, or -- for any other extension -- a DEM
    raster via :func:`terratrace.ingest.load_dem_array` (rasterio, lazily
    imported, so the common/offline paths never need it). Raises ``SystemExit`` on
    anything that is not a readable, non-empty 2-D array.
    """
    import numpy as np
    ext = os.path.splitext(path)[1].lower()
    try:
        if ext == ".npy":
            arr = np.load(path, allow_pickle=False)
        elif ext == ".json":
            with open(path, "r", encoding="utf-8") as fh:
                arr = json.load(fh)
        else:
            from terratrace import ingest
            arr, _posting_m = ingest.load_dem_array(path)
    except Exception as exc:
        raise SystemExit(f"terratrace: cannot load tile from {path!r}: {exc}")
    arr = np.asarray(arr, dtype=float)
    if arr.ndim != 2 or min(arr.shape) < 1:
        raise SystemExit(f"terratrace: input {path!r} is not a non-empty 2-D array")
    return arr


def _resolve_tile(use_synthetic, input_path):
    """Return a 2-D elevation tile from EXACTLY ONE of the synthetic generator or
    an input path. ``SystemExit(2)`` if both or neither are selected, so the
    offline-friendly ``--synthetic`` demo and a real ``--input`` are unambiguous.
    """
    if use_synthetic and input_path:
        raise SystemExit("terratrace: choose only one of --synthetic / --input")
    if not use_synthetic and not input_path:
        raise SystemExit("terratrace: provide --synthetic or --input PATH")
    return _synthetic_tile() if use_synthetic else _load_tile(input_path)


def _parse_point(text):
    """Parse a ``"row,col"`` CLI point into a ``(row, col)`` float tuple."""
    parts = str(text).split(",")
    if len(parts) != 2:
        raise SystemExit(f"terratrace: point {text!r} must be 'row,col'")
    try:
        return (float(parts[0]), float(parts[1]))
    except ValueError:
        raise SystemExit(f"terratrace: point {text!r} must be 'row,col' numbers")


def _emit_json(obj, out_path):
    """Write ``obj`` as pretty, key-sorted JSON to ``out_path`` (echoing the path)
    or print it to stdout. Mirrors the ``--out`` convention of the references /
    report subcommands; in stdout mode nothing but the JSON is printed, so the
    output pipes cleanly into a JSON parser."""
    text = json.dumps(obj, indent=2, sort_keys=True)
    if out_path:
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(text)
        print(out_path)
    else:
        print(text)


def _cmd_bank(argv):
    """Compute the full geomorphometric descriptor bank for one tile and emit JSON.

    The tile is either a deterministic synthetic scene (``--synthetic``, an
    offline demo like classify / sensitivity) or a 2-D elevation array loaded from
    ``--input`` (``.npy`` / JSON 2-D array / DEM raster); exactly one is required.
    ``--dx`` sets the (square) pixel size in metres; the JSON goes to ``--out``
    (path echoed) or stdout. This is a READ-ONLY analysis surface --
    :func:`terratrace.descriptors.descriptor_bank` is a flat bag of map-scale
    morphology descriptors consulted by NO decision in the engine; no
    traversability, mechanical, or mission claim is implied."""
    ap = argparse.ArgumentParser(
        prog="terratrace bank",
        description="Compute the full geomorphometric descriptor bank for one tile (JSON).")
    ap.add_argument("--synthetic", action="store_true",
                    help="use a deterministic synthetic tile (offline demo)")
    ap.add_argument("--input", default=None,
                    help="load the tile from PATH (.npy, JSON 2-D array, or a DEM raster)")
    ap.add_argument("--dx", type=float, default=1.0,
                    help="pixel size in metres (default 1.0)")
    ap.add_argument("--out", default=None,
                    help="write the JSON to this file instead of stdout")
    args = ap.parse_args(argv)
    if args.dx <= 0:
        raise SystemExit("--dx must be positive")
    z = _resolve_tile(args.synthetic, args.input)
    # Lazy import keeps `import terratrace.cli` cheap and dependency-free.
    from terratrace import descriptors
    _emit_json(descriptors.descriptor_bank(z, dx=args.dx), args.out)
    return 0


def _cmd_transect(argv):
    """Emit a transect signature (and optionally the full profile) along p0->p1.

    The tile comes from ``--synthetic`` or ``--input`` (the same loader as
    ``bank``). ``--p0`` / ``--p1`` are ``row,col`` pixel endpoints (defaults span
    the synthetic tile corner-to-corner) and ``--dx`` is the pixel size in metres.
    By default the flat scalar :func:`terratrace.transect.transect_signature` dict
    is emitted (so ``mean_slope`` etc. are top-level keys); ``--profile`` instead
    emits ``{"signature": ..., "profile": ...}`` with the full per-station
    :func:`terratrace.transect.extract_profile`. Output goes to ``--out`` or
    stdout. Purely geometric map-scale morphology -- see the transect module's
    claim firewall."""
    ap = argparse.ArgumentParser(
        prog="terratrace transect",
        description="Emit a transect signature (and optional profile) along p0->p1 (JSON).")
    ap.add_argument("--synthetic", action="store_true",
                    help="use a deterministic synthetic tile (offline demo)")
    ap.add_argument("--input", default=None,
                    help="load the tile from PATH (.npy, JSON 2-D array, or a DEM raster)")
    ap.add_argument("--p0", default="2,2", help="start point 'row,col' (default 2,2)")
    ap.add_argument("--p1", default="45,45", help="end point 'row,col' (default 45,45)")
    ap.add_argument("--dx", type=float, default=1.0,
                    help="pixel size in metres (default 1.0)")
    ap.add_argument("--profile", action="store_true",
                    help="also include the full per-station profile in the output")
    ap.add_argument("--out", default=None,
                    help="write the JSON to this file instead of stdout")
    args = ap.parse_args(argv)
    if args.dx <= 0:
        raise SystemExit("--dx must be positive")
    p0, p1 = _parse_point(args.p0), _parse_point(args.p1)
    z = _resolve_tile(args.synthetic, args.input)
    # Lazy import keeps `import terratrace.cli` cheap and dependency-free.
    from terratrace import transect
    sig = transect.transect_signature(z, p0, p1, dx=args.dx)
    if args.profile:
        out = {"signature": sig,
               "profile": transect.extract_profile(z, p0, p1, dx=args.dx)}
    else:
        out = sig
    _emit_json(out, args.out)
    return 0


def _cmd_version(argv):
    """Print the package version and the study-schema version."""
    ap = argparse.ArgumentParser(
        prog="terratrace version",
        description="Print the TerraTrace version and study-schema version.")
    ap.parse_args(argv)
    print(f"terratrace {_PACKAGE_VERSION} (schema {_SCHEMA_VERSION})")
    return 0


_DISPATCH = {
    "study": _cmd_study,
    "validate": _cmd_validate,
    "benchmark": _cmd_benchmark,
    "report": _cmd_report,
    "report-html": _cmd_report_html,
    "dossier": _cmd_dossier,
    "references": _cmd_references,
    "sensitivity": _cmd_sensitivity,
    "classify": _cmd_classify,
    "confidence": _cmd_confidence,
    "bank": _cmd_bank,
    "transect": _cmd_transect,
    "version": _cmd_version,
}


def _print_top_help():
    """Print the top-level command summary and the legacy-fallback note."""
    print("usage: python -m terratrace.cli <command> [options]")
    print()
    print("TerraTrace unified command dispatcher.")
    print()
    print("commands:")
    print("  study      run the synthetic reference study and write artifacts (default)")
    print("  validate   run the scientific-correctness validation suite")
    print("  benchmark  run the reproducibility + scaling benchmark")
    print("  report     render a markdown report from a study JSON")
    print("  report-html render a self-contained HTML report from a study JSON")
    print("  dossier    print a per-candidate site dossier from a study JSON")
    print("  references  print the data-sources citation / credits bundle (Markdown)")
    print("  sensitivity run a decision-lens robustness ablation on a synthetic scene")
    print("  classify    label synthetic terrains by map-scale morphology type")
    print("  confidence  print the non-composite decision confidence for a study JSON")
    print("  bank        compute the full geomorphometric descriptor bank for one tile (JSON)")
    print("  transect    emit a transect signature (and optional profile) along a line (JSON)")
    print("  version    print the TerraTrace version and schema version")
    print()
    print("Run 'python -m terratrace.cli <command> -h' for a command's options.")
    print("With no known command, options route to 'study' (legacy mode).")


def main(argv=None):
    """Dispatch to a subcommand, defaulting to the legacy ``study`` behaviour.

    The public ``main(argv)`` signature is preserved: callers get back an int
    exit code (0 = success). A known first token selects that command; a
    bareword that is not a command fails cleanly; an empty or dash-led argv is
    routed to the implicit ``study`` command (legacy options such as ``--out``).
    """
    argv = list(sys.argv[1:] if argv is None else argv)

    if argv and argv[0] in ("-h", "--help"):
        _print_top_help()
        return 0
    if argv and argv[0] in _DISPATCH:
        command, rest = argv[0], argv[1:]
    elif argv and not argv[0].startswith("-"):
        sys.stderr.write(f"terratrace: unknown command {argv[0]!r}; "
                         f"choose from {', '.join(_DISPATCH)}\n")
        raise SystemExit(2)
    else:
        command, rest = "study", argv
    return _DISPATCH[command](rest)


if __name__ == "__main__":
    raise SystemExit(main())
