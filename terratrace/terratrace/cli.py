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

# Mirrors study.compare_units' package schema_version; a constant keeps the
# `version` command instant (no study run, no heavy import).
_SCHEMA_VERSION = "0.1.0"


def _cmd_study(argv):
    """Legacy behaviour: run the synthetic study and write the artifact set."""
    ap = argparse.ArgumentParser(
        prog="terratrace study",
        description="Run the synthetic reference study and emit a study package.")
    ap.add_argument("--out", default="artifacts", help="output directory")
    ap.add_argument("--target-support-m", type=float, default=100.0)
    ap.add_argument("--native-posting-m", type=float, default=25.0)
    args = ap.parse_args(argv)
    if args.target_support_m <= 0 or args.native_posting_m <= 0:
        raise SystemExit("--target-support-m and --native-posting-m must be positive")

    from .study import run_study
    from .provenance import sha256_json

    pkg = run_study(target_support_m=args.target_support_m,
                    native_posting_m=args.native_posting_m)

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
        "release": "terratrace-v0.1.0",
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

    print(f"result_state       = {pkg['result_state']}")
    print(f"recommended_unit   = {pkg['recommended_unit']}")
    print(f"package_hash       = {pkg['package_hash'][:16]}...")
    print(f"artifacts written  -> {args.out}")
    return 0


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


def _cmd_version(argv):
    """Print the package version and the study-schema version."""
    ap = argparse.ArgumentParser(
        prog="terratrace version",
        description="Print the TerraTrace version and study-schema version.")
    ap.parse_args(argv)
    import terratrace
    print(f"terratrace {terratrace.__version__} (schema {_SCHEMA_VERSION})")
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
