"""Documentation-consistency guards — the prose must match the code.

These are the cheap, always-on half of the documentation guard: they run the structural
checks in ``scripts/doc_consistency_check.py`` over this tree, so a page that never reaches
the nav, a rotted relative link, a version that drifted between three files, or a stale
"686 tests" is a failing test rather than an invisible defect. (The script is also a CI step
in its own right.)

House style: module-level ``def test_*()`` functions, no pytest, no optional imports.
"""
import importlib.util
import pathlib
import re

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent                      # .../terratrace


def _load_guard():
    spec = importlib.util.spec_from_file_location(
        "doc_consistency_check", _ROOT / "scripts" / "doc_consistency_check.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_doc_counts_match_the_code():
    """Every canonical document states the real counts, computed from the source."""
    g = _load_guard()
    problems = []
    g.check_counts(problems)
    assert not problems, "count drift:\n" + "\n".join(problems)


def test_doc_versions_are_in_sync():
    """`terratrace.__version__` == pyproject.toml == CITATION.cff."""
    g = _load_guard()
    problems = []
    ver = g.check_versions(problems)
    assert not problems, "version drift:\n" + "\n".join(problems)
    assert ver, "no version was resolved"


def test_every_docs_page_is_in_the_nav():
    """A page a reader cannot reach through the nav is a missing page."""
    g = _load_guard()
    problems = []
    g.check_nav(problems)
    assert not problems, "nav problems:\n" + "\n".join(problems)


def test_relative_links_resolve():
    """No relative Markdown link points at a path that does not exist."""
    g = _load_guard()
    problems = []
    n = g.check_links(problems)
    assert not problems, "broken links:\n" + "\n".join(problems)
    assert n > 20, f"expected the doc set to contain real links, found {n}"


def test_v3_verdicts_are_quoted_with_their_caveat():
    """The v3 headline must not appear without the pre-specification caveat."""
    g = _load_guard()
    problems = []
    g.check_claims(problems)
    assert not problems, "claim problems:\n" + "\n".join(problems)


def test_the_count_patterns_catch_stale_prose_and_ignore_commands():
    """The guard's own regexes: they must catch a stale count and not fire on a command name.

    A guard that cannot reproduce the failure is decoration, so this pins the two false
    alarms that were actually observed while building it ("python3 tests/…" reading as
    "3 tests", and "COP30 product" reading as "30 product").
    """
    g = _load_guard()
    tests_pat = re.compile(g.COUNT_RES["test count"])
    src_pat = re.compile(g.COUNT_RES["source count"])

    assert tests_pat.search("the suite has 686 tests now").group(1) == "686"
    assert tests_pat.search("837 offline tests").group(1) == "837"
    assert tests_pat.search("python3 tests/run_tests.py") is None
    assert tests_pat.search("run_tests.py    # 837 tests").group(1) == "837"

    assert src_pat.search("a 13-product catalog").group(1) == "13"
    assert src_pat.search("13-source registry").group(1) == "13"
    assert src_pat.search("COP30 product") is None
    assert src_pat.search("GLO-30 tiles") is None
