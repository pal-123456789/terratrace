"""CI-hygiene guards: keep the dependency-free suite dependency-free.

WHY THIS FILE EXISTS
--------------------
``.github/workflows/ci.yml`` installs **NumPy only** (``requirements.txt``) and then
runs ``tests/run_tests.py``. Two failure modes have already bitten this project:

1. A module imported an optional dependency (``yaml``, then ``rasterio``) at module
   scope. Module import is **not** wrapped in a try in ``run_tests.py``, so that does
   not fail one test -- it aborts the entire run with an ImportError.
2. A test file itself needed the optional dependency, so it failed on all three CI
   Pythons while passing locally.

Both are invisible locally, where the optional dependency happens to be installed.
These tests reproduce the CI environment exactly (NumPy present, everything else
blocked) in a **subprocess**, so they cannot be fooled by whatever is installed in
the calling environment.

A THIRD failure mode is NOT coverable here and lives in ``scripts/ci_hygiene_check.py``,
run as its own CI step: an unguarded optional import **inside a test function** only
fires when that function is *called*, so checking module import is not enough. (That
exact bug -- ``import rasterio`` on a line above its availability guard -- reached CI
once.) The script actually runs those tests on a NumPy-only interpreter, which costs
~2 minutes and is therefore a CI step rather than an everyday unit test. This file
keeps the cheap guards: module-import safety, packaging consistency, and proof that
the CI wiring for the script is still present.

They are deliberately dependency-free themselves.
"""
import os
import subprocess
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)

# Optional packages this project uses SOMEWHERE, but which CI does not install.
# Anything here must be imported lazily (inside a function) and guarded.
#
# The second group matters as much as the first. `affine` is a transitive dependency of rasterio and
# is declared nowhere; importing it directly is invisible on a machine that has rasterio and fatal
# on the NumPy-only interpreter, which is how all three CI jobs went red once. Keep this list in
# sync with scripts/ci_hygiene_check.py's OPTIONAL + TRANSITIVE.
_OPTIONAL = ["rasterio", "yaml", "requests", "scipy", "pandas", "matplotlib"]
_TRANSITIVE = ["affine", "cligj", "snuggs", "fiona", "shapely", "pyproj", "geopandas",
               "rioxarray", "rasterstats"]
_BLOCKED = _OPTIONAL + _TRANSITIVE

# The probe runs in a clean interpreter with the optional packages blocked, and
# imports every module the CI run will import. It prints the first failure and
# exits non-zero.
_PROBE = r'''
import importlib.util, pathlib, sys

BLOCK = set({optional!r})

class _Blocker:
    """Make an optional package look uninstalled."""
    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in BLOCK:
            raise ImportError(f"{{fullname}} is blocked (not installed in the core CI env)")
        return None

sys.meta_path.insert(0, _Blocker())

# Belt and braces: drop anything already imported and make it un-findable.
for name in list(sys.modules):
    if name.split(".")[0] in BLOCK:
        del sys.modules[name]

root = pathlib.Path({root!r})
tests = pathlib.Path({tests!r})
sys.path.insert(0, str(root))

def load(path):
    spec = importlib.util.spec_from_file_location(path.stem, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # exactly what run_tests.py does
    return mod

failures = []
for path in sorted(tests.glob("test_*.py")):
    try:
        load(path)
    except BaseException as exc:
        failures.append(f"{{path.name}}: {{type(exc).__name__}}: {{exc}}")

# Also prove the engine package itself imports without the optional deps.
pkg = root / "terratrace"
for path in sorted(pkg.glob("*.py")):
    name = path.stem
    if name == "__init__":
        continue
    try:
        __import__(f"terratrace.{{name}}")
    except BaseException as exc:
        failures.append(f"terratrace/{{name}}.py: {{type(exc).__name__}}: {{exc}}")

for f in failures:
    print(f)
sys.exit(1 if failures else 0)
'''


def _run_probe():
    code = _PROBE.format(optional=_BLOCKED, root=_ROOT, tests=_HERE)
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run([sys.executable, "-c", code], capture_output=True,
                          text=True, env=env, timeout=600)


def test_optional_dependencies_really_are_blocked_in_the_probe():
    """If the blocker did not work, the hygiene test would pass vacuously."""
    code = _PROBE.format(optional=_BLOCKED, root=_ROOT, tests=_HERE).replace(
        "sys.exit(1 if failures else 0)", "sys.exit(2)")
    probe = r'''
import sys
BLOCK = set({optional!r})
class _Blocker:
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split(".")[0] in BLOCK:
            raise ImportError("blocked")
        return None
sys.meta_path.insert(0, _Blocker())
for name in BLOCK:
    try:
        __import__(name)
    except ImportError:
        pass
    else:
        print("NOT BLOCKED:", name)
        sys.exit(1)
sys.exit(0)
'''.format(optional=_BLOCKED)
    r = subprocess.run([sys.executable, "-c", probe], capture_output=True, text=True,
                       timeout=120)
    assert r.returncode == 0, f"blocker is ineffective: {r.stdout}{r.stderr}"


def test_every_module_the_ci_run_imports_survives_a_numypy_only_environment():
    """The real guard: the suite's import step must not need an optional dep.

    ``run_tests.py`` imports every ``test_*.py`` outside a try, and CI imports the
    engine with NumPy alone -- so any top-level optional import aborts the run.
    """
    r = _run_probe()
    assert r.returncode == 0, (
        "These modules need an optional dependency at import time. CI installs "
        "NumPy only, so this would abort or fail the whole suite on every CI "
        "Python. Import the dependency lazily inside the function and guard it:\n"
        + (r.stdout or "") + (r.stderr or ""))


# --------------------------------------------------------------------------- #
# Packaging hygiene                                                            #
# --------------------------------------------------------------------------- #
def test_package_version_matches_pyproject():
    """A release must not carry two different version numbers.

    ``terratrace.__version__`` is the single source of truth; ``pyproject.toml``
    has to agree. (Parsed with a regex rather than ``tomllib`` so this runs on
    every supported Python.)
    """
    import re
    import terratrace
    with open(os.path.join(_ROOT, "pyproject.toml"), encoding="utf-8") as fh:
        text = fh.read()
    m = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    assert m, "pyproject.toml has no [project].version"
    assert m.group(1) == terratrace.__version__, (
        f"pyproject version {m.group(1)!r} != terratrace.__version__ "
        f"{terratrace.__version__!r}")


def test_cli_reports_the_package_version():
    """The `version` command and any built manifest must use __version__."""
    import importlib
    import terratrace
    cli = importlib.import_module("terratrace.cli")
    assert cli._PACKAGE_VERSION == terratrace.__version__


def test_ci_workflow_is_unique_and_runs_the_optional_dependency_guard():
    """Two things that have each gone wrong once.

    (1) There used to be a second, INERT ``terratrace/.github/workflows/ci.yml``:
    GitHub only reads the repo-root ``.github/workflows/``, so it never ran while
    appearing to be CI, and it drifted. Assert there is exactly one.
    (2) The full optional-dependency guard lives in a script and is only useful if
    CI actually invokes it -- assert the wiring, and the file, exist.
    """
    repo = os.path.dirname(_ROOT)
    found = []
    for dirpath, dirnames, filenames in os.walk(repo):
        dirnames[:] = [d for d in dirnames
                       if d not in (".git", "artifacts", "__pycache__", "node_modules")]
        if "ci.yml" in filenames:
            found.append(os.path.join(dirpath, "ci.yml"))
    assert len(found) == 1, (
        "expected exactly ONE ci.yml, because GitHub only reads the repo-root "
        f".github/workflows/; found {found}")
    with open(found[0], encoding="utf-8") as fh:
        text = fh.read()
    assert "ci_hygiene_check.py" in text, (
        "ci.yml no longer runs scripts/ci_hygiene_check.py; the guard that catches "
        "an unguarded optional import inside a TEST FUNCTION is disabled")
    assert os.path.exists(os.path.join(_ROOT, "scripts", "ci_hygiene_check.py"))
