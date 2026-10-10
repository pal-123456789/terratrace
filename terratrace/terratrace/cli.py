"""Unified TerraTrace command-line dispatcher.

Usage: ``python -m terratrace.cli <command> [options]``

Commands:
  study      run the synthetic reference study and emit a study package (default)
  validate   run the scientific-correctness validation suite
  benchmark  run the reproducibility + scaling benchmark
  report     render a markdown report from a study JSON
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
