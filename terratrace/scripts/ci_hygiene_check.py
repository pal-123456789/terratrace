"""Run the optional-dependency-touching tests on a NumPy-only interpreter.

WHY THIS IS A SCRIPT AND NOT A UNIT TEST
-----------------------------------------
``.github/workflows/ci.yml`` installs **NumPy only** and then runs the suite. Any
test that reaches for ``rasterio``/``yaml``/``requests`` must therefore skip
*cleanly*, and -- this is the part that bites -- the availability guard must come
**before** the optional import, because ``import rasterio`` on a line above the
guard still raises on CI.

That exact bug reached CI once (``test_read_cog30_writes_a_readable_geotiff``),
and a module-import-only check did not catch it: module import succeeds, and only
*calling* the function fails. So the check has to actually RUN the tests.

Running them costs ~2 minutes, which is too slow to sit inside the normal suite,
so it lives here and is invoked as its own CI step. ``tests/test_ci_hygiene.py``
keeps the cheap always-on guards (module import safety, packaging consistency).

Scope is derived, not hard-coded: every test module that mentions an optional
dependency by name is included, so a newly added test that imports ``rasterio``
is covered automatically without editing this file.

Usage::

    python scripts/ci_hygiene_check.py          # exit 0 = clean
"""
from __future__ import annotations

import argparse
import importlib.util
import pathlib
import sys
import traceback

ROOT = pathlib.Path(__file__).resolve().parent.parent
TESTS = ROOT / "tests"

# Packages the core CI environment does NOT install. Keep in sync with
# requirements.txt (core) vs pyproject [project.optional-dependencies].real.
OPTIONAL = ("rasterio", "yaml", "requests", "scipy", "pandas", "matplotlib")

# And the packages those bring in. These matter as much as the direct ones, and this list exists
# because of a real failure: `common_grid.destination_grid` imported `affine` directly — a
# transitive dependency of rasterio that is declared nowhere — and turned all three CI interpreters
# red while this check stayed green, because `affine` was not blocked here and the local machine has
# it. A guard that only simulates the dependencies you remembered is not simulating the environment.
TRANSITIVE = ("affine", "cligj", "snuggs", "fiona", "shapely", "pyproj", "geopandas",
              "rioxarray", "rasterstats")

BLOCKED = OPTIONAL + TRANSITIVE

# The suite's own skip convention (tests/harness.py). A test that cannot exercise its claim on this
# interpreter raises this with a reason; that is the honest outcome here, not a failure, and it must
# not be silently counted as a pass either.
if str(TESTS) not in sys.path:
    sys.path.insert(0, str(TESTS))
try:
    from harness import Skip as _Skip
except Exception:                                            # pragma: no cover
    class _Skip(Exception):
        pass


class _Blocker:
    """Make an optional package look uninstalled."""

    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCKED:
            raise ImportError(
                f"{fullname} is not installed in the core environment "
                f"(NumPy only), so this behaves as it does on CI")
        return None


def _install_blocker():
    sys.meta_path.insert(0, _Blocker())
    for name in list(sys.modules):
        if name.split(".")[0] in BLOCKED:
            del sys.modules[name]


def _load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _mentions_optional(path):
    text = path.read_text(encoding="utf-8")
    return any(dep in text for dep in OPTIONAL)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="run EVERY test module, not just the ones naming an "
                         "optional dependency (slow; the targeted set is the "
                         "default because it is where the risk is)")
    args = ap.parse_args(argv)

    _install_blocker()
    sys.path.insert(0, str(ROOT))

    failures = []

    # (1) Every engine module must import with NumPy alone. run_tests.py imports
    #     test modules outside a try, so a single bad import aborts the suite.
    for path in sorted((ROOT / "terratrace").glob("*.py")):
        if path.stem == "__init__":
            continue
        try:
            __import__(f"terratrace.{path.stem}")
        except BaseException as exc:
            failures.append(f"terratrace/{path.name}: {type(exc).__name__}: {exc}")

    # (2) Test modules that touch an optional dependency: import AND run, because
    #     an unguarded import inside a function only fails when it is called.
    modules = sorted(TESTS.glob("test_*.py"))
    selected = modules if args.all else [p for p in modules if _mentions_optional(p)]
    passed = skipped = 0
    skips = []
    for path in selected:
        try:
            mod = _load(path)
        except BaseException as exc:
            failures.append(f"{path.name}: import failed: {type(exc).__name__}: {exc}")
            continue
        for name in sorted(dir(mod)):
            if not name.startswith("test_") or not callable(getattr(mod, name)):
                continue
            try:
                getattr(mod, name)()
                passed += 1
            except _Skip as exc:
                # A test that DECLINES to run on this interpreter, with a reason, is the desired
                # outcome on a NumPy-only environment -- not a defect. Counting it as a failure
                # would punish exactly the honest behaviour, and counting it as a pass would let a
                # never-executed claim look verified. It is counted, and reported, as a skip.
                skipped += 1
                skips.append(f"{path.name}::{name}: {exc}")
            except BaseException as exc:
                failures.append(f"{path.name}::{name}: {type(exc).__name__}: {exc}")
                if args.all:
                    traceback.print_exc()

    print(f"ci_hygiene_check: {len(selected)}/{len(modules)} test module(s), "
          f"{passed} test function(s) run, {skipped} declined, with "
          f"{', '.join(BLOCKED)} blocked")
    for s in skips:
        print(f"  skip  {s}")
    if failures:
        print(f"\nFAILED ({len(failures)}):")
        for f in failures:
            print("  " + f)
        print("\nAn optional dependency was reached. Import it lazily inside the "
              "function AND put the availability guard BEFORE the import.")
        return 1
    print("OK -- the suite is safe on a NumPy-only interpreter")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
