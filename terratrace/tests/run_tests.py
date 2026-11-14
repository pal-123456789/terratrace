"""Dependency-free test runner (no pytest required).

Discovers test_*.py modules in this directory, runs every test_* function,
and reports a summary. Exits non-zero on any failure.

Tests may raise ``harness.Skip`` when this environment cannot exercise them (a missing optional
dependency, an absent dataset). Those are reported as SKIP with their reason and counted
separately: a skip is not a pass, and a summary that hides the difference lets a reader mistake
"the suite is green" for "everything was verified".
"""
import importlib.util
import pathlib
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


def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
