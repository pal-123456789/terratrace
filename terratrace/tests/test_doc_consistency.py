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
    fix_pat = re.compile(g.COUNT_RES["fixture count"])

    assert tests_pat.search("the suite has 686 tests now").group(1) == "686"
    assert tests_pat.search("837 offline tests").group(1) == "837"
    assert tests_pat.search("python3 tests/run_tests.py") is None
    assert tests_pat.search("run_tests.py    # 837 tests").group(1) == "837"

    assert src_pat.search("a 13-product catalog").group(1) == "13"
    assert src_pat.search("13-source registry").group(1) == "13"
    assert src_pat.search("14 catalogued products").group(1) == "14"
    assert src_pat.search("COP30 product") is None
    assert src_pat.search("GLO-30 tiles") is None
    # a UNIT is not an adjective: these are measurements, not counts of sources. The pattern read
    # them as counts the first time such a phrase was written in this repository's own prose.
    for measured in ("a 40 MB product", "30 m resolution products", "1 km products",
                     "40 MB of raster products"):
        assert src_pat.search(measured) is None, f"{measured!r} was read as a source count"

    # "# 891 fixtures" is how two canonical pages stated the test count, and the pattern above —
    # which needs the word `tests` to follow the number — never saw either, so both sat stale.
    assert fix_pat.search("# 891 fixtures").group(1) == "891"
    assert fix_pat.search("(891 fixtures, `tests/run_tests.py`)").group(1) == "891"
    assert fix_pat.search("891 fixtures and 51 oracles").group(1) == "891"
    assert fix_pat.search("891 fixtures\n").group(1) == "891"
    # and the two forms that are NOT the test count, each of which a looser pattern matched when it
    # was first written (the first one is why this is a separate pattern at all)
    assert fix_pat.search("the 6 fixture tiles") is None
    assert fix_pat.search("a 2x2 fixture") is None
    assert fix_pat.search("12,960,000 values") is None


def test_site_routes_resolve_the_way_a_static_host_publishes_them():
    """The three live routes must resolve, with and without their trailing slash.

    This is the guard's deployment-facing half. The site is published from ``site/``, so a URL is
    relative to that directory — and the moment the links moved to their canonical trailing-slash
    form (which is what GitHub Pages serves), a resolver that assumed the repository root broke
    every route at once. That failure mode is why this is asserted rather than assumed.
    """
    g = _load_guard()
    repo = g.REPO
    expect = {
        "/": "site/index.html",
        "/study": "site/study/index.html",
        "/study/": "site/study/index.html",
        "/viewer": "site/viewer/index.html",
        "/viewer/": "site/viewer/index.html",
    }
    for route, want in expect.items():
        got = g.resolve_site_route(route)
        assert got.exists(), f"{route!r} resolved to {got}, which does not exist"
        assert got.relative_to(repo).as_posix() == want, f"{route!r} -> {got}, expected {want}"

    # and a route that does not exist must still fail, or the check above proves nothing
    assert not g.resolve_site_route("/no-such-page/").exists()


def test_the_deployment_shape_is_intact():
    """``site/`` stays deployable: the domain marker, the no-Jekyll marker, and a real tree.

    Cheap, and each piece has a silent failure: a missing ``.nojekyll`` makes Pages drop
    leading-underscore paths without error, and a wrong ``CNAME`` puts the site on the wrong host.
    """
    site = _ROOT.parent / "site"
    assert (site / "CNAME").read_text(encoding="utf-8").strip() == "terratrace.fit", \
        "site/CNAME must name the published domain exactly"
    assert (site / ".nojekyll").exists(), \
        "site/.nojekyll is missing — GitHub Pages will run Jekyll and drop _-prefixed paths"
    assert (site / "index.html").exists()
    for name in ("study", "viewer"):
        assert (site / name / "index.html").exists(), f"site/{name}/index.html is missing"

    # every internal href the site uses must resolve — the deploy can then not 404 on a route
    g = _load_guard()
    problems = []
    g.check_links(problems)
    assert not problems, "site link problems:\n" + "\n".join(problems)


def test_the_markup_check_reproduces_the_defect_it_was_written_for():
    """A guard that cannot reproduce its target failure is decoration.

    The defect: an edited block in site/index.html closed one </div> too many, which un-nested the
    rest of the document while leaving every link perfectly resolvable — so the link check passed
    and the page rendered wrong. This builds a temporarily unbalanced copy and asserts the new check
    names the file, then restores it.

    It also pins how the check NAMES the file, which is a second defect this test found later and on
    one platform only. On Windows `str(Path)` yields backslashes, so the guard printed
    ``markup: site\\index.html`` and the assertion below — looking for ``site/index.html`` — failed
    on the developer's machine while passing on Linux CI, where the separator happens to be the one
    the test wants. A message whose text depends on the OS is a defect in the guard, not in the
    test: on Linux it is invisible, which is precisely why it needs a structural assertion as well.
    """
    g = _load_guard()
    page = g.REPO / "site" / "index.html"
    original = page.read_text(encoding="utf-8")

    # the guard must format every repo-relative path through _rel(), on every platform
    guard_src = (_ROOT / "scripts" / "doc_consistency_check.py").read_text(encoding="utf-8")
    raw = re.findall(r"\{[A-Za-z_]+\.relative_to\(REPO\)\}", guard_src)
    assert not raw, (
        "a repo-relative path is interpolated into a message without .as_posix(), so the message "
        f"will use backslashes on Windows: {raw}. Format it through _rel() instead."
    )
    rel_fn = getattr(g, "_rel", None)
    assert rel_fn is not None, "_rel() is gone; messages are back to platform-dependent paths"
    assert rel_fn(g.REPO / "site" / "index.html") == "site/index.html", (
        "a repo-relative path is reported as "
        f"{rel_fn(g.REPO / 'site' / 'index.html')!r}, not 'site/index.html'"
    )

    # a genuinely unbalanced copy: drop one closing tag from the document
    marker = "</main>"
    assert marker in original
    broken = original.replace(marker, "", 1)
    try:
        page.write_text(broken, encoding="utf-8")
        problems = []
        g.check_site_markup(problems)
        assert problems, "the markup check did not notice a missing </main>"
        assert any("site/index.html" in p for p in problems), problems
        assert all("\\" not in p for p in problems), (
            "a markup problem message uses a backslash-separated path, which only happens on "
            f"Windows — the message text must not depend on the OS: {problems}"
        )
    finally:
        page.write_text(original, encoding="utf-8")   # always restore, even if the assert fires

    # restored: the check is clean again
    problems = []
    g.check_site_markup(problems)
    assert not problems, "the markup check reports the restored page as broken:\n" + "\n".join(problems)


def test_the_markup_check_is_clean_on_the_published_pages():
    """And the shipped pages pass, so the check is not vacuous."""
    g = _load_guard()
    problems = []
    n = g.check_site_markup(problems)
    assert n >= 3, f"expected the three published pages, checked {n}"
    assert not problems, "published pages are not tag-balanced:\n" + "\n".join(problems)


def test_a_stale_count_in_a_slide_caption_is_caught():
    """The deck generators print counts twice: a bare string and a labelled helper argument.

    Every regex the guard owns is anchored on a number immediately followed by its noun, so the
    helper form — ``stat(s, x, y, w, "NNN", "offline tests — ...", ACC)`` — walks straight past all
    of them. That is not hypothetical: it is how a shipped slide carried a wrong scalar count for a
    whole release. This seeds the defect in the real generator, asserts the check names the file,
    and restores it.

    The stale value is derived from whatever the generator currently says rather than hard-coded, so
    this test does not itself go stale every time the suite grows.
    """
    g = _load_guard()
    script = g.ROOT / "scripts" / "build_deck.js"
    original = script.read_text(encoding="utf-8")
    m = re.search(r'"(\d+)", "offline tests', original)
    assert m, "the deck no longer prints its test count the way this test expects"
    stale = original[:m.start(1)] + str(int(m.group(1)) + 1) + original[m.end(1):]

    try:
        script.write_text(stale, encoding="utf-8")
        problems = []
        g.check_counts(problems)
        assert any("build_deck.js" in p for p in problems), (
            "a stale test count inside a slide caption went unnoticed:\n" + "\n".join(problems)
        )
    finally:
        script.write_text(original, encoding="utf-8")

    # restored, and the guard is clean again — which is also the check above's positive control
    problems = []
    g.check_counts(problems)
    assert not problems, "the restored deck generator still reports problems:\n" + "\n".join(problems)

