"""Dependency-free test runner (no pytest required).

Discovers test_*.py modules in this directory, runs every test_* function,
and reports a summary. Exits non-zero on any failure.

Tests may raise ``harness.Skip`` when this environment cannot exercise them (a missing optional
dependency, an absent dataset). Those are reported as SKIP with their reason and counted
separately: a skip is not a pass, and a summary that hides the difference lets a reader mistake
"the suite is green" for "everything was verified".
"""
import argparse
import importlib.util
import pathlib
import re
import sys
import traceback

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(HERE))          # `import harness`

try:
    from harness import Skip
except Exception:                       # pragma: no cover - harness is part of the repo
    class Skip(Exception):
        pass

# A skip whose reason looks like this is a BROKEN ENVIRONMENT, not an absent dataset: the package
# is simply not installed. The distinction matters in the scientific CI job, where the geospatial
# stack IS installed, so a dependency skip there means the job is misconfigured -- and a suite that
# reports it as an ordinary skip would hide a scientific path that never ran.
DEPENDENCY_SKIP = re.compile(r"no module named|is not installed|unavailable|pip install",
                             re.IGNORECASE)


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--strict-skips", action="store_true",
                    help="exit non-zero if any skip was caused by a missing PACKAGE rather than an "
                         "absent dataset. Used by the scientific CI job, where the geospatial stack "
                         "is installed and a dependency skip therefore means the job is wrong.")
    args = ap.parse_args(argv)

    passed = failed = skipped = 0
    failures = []
    skips = []
    for path in sorted(HERE.glob("test_*.py")):
        mod = load(path)
        for name in sorted(dir(mod)):
            if not name.startswith("test_"):
                continue
            fn = getattr(mod, name)
            if not callable(fn):
                continue
            try:
                fn()
                passed += 1
                print(f"PASS {path.name}::{name}")
            except Skip as exc:
                skipped += 1
                skips.append(f"{path.name}::{name}: {exc}")
                print(f"SKIP {path.name}::{name}")
            except Exception:
                failed += 1
                failures.append(f"{path.name}::{name}\n{traceback.format_exc()}")
                print(f"FAIL {path.name}::{name}")
    print("\n" + "=" * 60)
    print(f"passed={passed} failed={failed} skipped={skipped}")
    if skips:
        print("\nSKIPPED (this environment could not exercise these - not verified here):")
        for s in skips:
            print(f"  - {s}")
    if failures:
        print("\n" + "\n".join(failures))
        return 1
    if args.strict_skips:
        offenders = [s for s in skips if DEPENDENCY_SKIP.search(s)]
        if offenders:
            print("\nSTRICT SKIPS: the environment is missing packages it was told to install, so "
                  "these are broken runs rather than absent-data skips:")
            for s in offenders:
                print(f"  - {s}")
            return 1
        print(f"\nSTRICT SKIPS: all {skipped} skip(s) are absent-dataset skips; no dependency is "
              f"missing from this environment.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
