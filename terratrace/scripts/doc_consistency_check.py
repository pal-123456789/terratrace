"""Documentation-consistency check — the prose must match the code.

A documentation bug is invisible. Nothing fails when a README states a test count that is
hundreds out of date, or when a page is added to ``docs/`` and never wired into the nav, or
when a relative link rots. Judges and users read the prose first, so prose drift is a real
defect.

This script makes that class of drift loud and mechanical. It is cheap — a few hundred
milliseconds, no test execution: the test count is derived by AST-parsing the test modules
exactly the way the dependency-free runner discovers them (module-level ``def test_*``), so
the number is *computed*, never typed.

It checks, against the tree it is run in:

1. **COUNTS**  — the canonical documents state the real test / oracle / catalog-source /
   module / descriptor-family counts, computed here from the source. A window-dependent
   count (leaf scalars) is checked against the measured *range* instead of a single value.
2. **VERSION** — ``terratrace.__version__`` == ``pyproject.toml`` == ``CITATION.cff``.
3. **NAV**     — every ``docs/**/*.md`` page is reachable from ``mkdocs.yml``, and every nav
   entry points at a file that exists.
4. **LINKS**   — every relative Markdown link resolves **for a reader of the repository**, i.e.
   against the *tracked* file set rather than the working tree (a link into a git-ignored directory
   is broken however present it is on the author's disk); and on the website, every internal
   ``href`` resolves through the ``vercel.json`` rewrites and every ``#fragment`` has a real
   target (a page can look fine in the repo and still 404 in the browser).
5. **CLAIMS**  — the frozen benchmark verdicts quoted in the live docs still match
   ``docs/RESULTS-v3.md`` (a headline that silently loses its caveat is a defect too).
6. **MARKUP**  — every published HTML page is tag-balanced. The link check walks ``href``\ s and
   cannot see a stray ``</div>``, and an unbalanced page renders wrong in the browser while every
   link in it still resolves. This was added after exactly that mistake: an edited block on
   ``site/index.html`` closed one ``</div>`` too many and un-nested the rest of the document.

Historical records (``CHANGELOG.md``, ``CLAIM-LEDGER.md``, ``RESULTS-*``, ``REAL-EXAMPLE.md``,
``BENCHMARK-PROTOCOL*``) are exempt from (1): they are dated records of what was true *then*,
and rewriting them would destroy the audit trail rather than fix a bug.

Usage:
    python scripts/doc_consistency_check.py          # from terratrace/
    python scripts/doc_consistency_check.py --quiet
Exits 0 when consistent, 1 with a named list of problems otherwise.
"""
from __future__ import annotations

import ast
import pathlib
import re
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                      # .../terratrace
REPO = ROOT.parent                      # repository root
sys.path.insert(0, str(ROOT))


def _tracked():
    """Repo-relative paths a fresh clone would have, or ``None`` if git is unavailable.

    This is the whole point of the link check. A path that exists on the author's disk because
    it is git-ignored does NOT exist for anyone who clones the repository — so a link to it is
    broken, however green the local run looks. Checking the filesystem alone gets this wrong;
    the first version of this guard did, and CI caught it.
    """
    try:
        out = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                             capture_output=True, text=True, check=True).stdout
    except Exception:
        return None
    return set(p for p in out.split() if p)


TRACKED = _tracked()


def _readable(target: pathlib.Path) -> bool:
    """Would a reader of the repository find this path? Directories count if they hold tracked files."""
    if not target.exists():
        return False
    if TRACKED is None:
        return True                     # no git (e.g. an exported tarball) — trust the filesystem
    # Normalise before comparing: a link like ``../CLEAN-ROOM-NOTE.md`` exists on disk (the OS
    # collapses the ``..``) but as a *string* it is not in the tracked list, so the raw comparison
    # reports a false break. ``.resolve()`` matches how REPO itself was derived.
    target = target.resolve()
    try:
        rel = target.relative_to(REPO).as_posix()
    except ValueError:
        return True                     # outside the repo — not ours to police
    if rel in TRACKED:
        return True
    if target.is_dir():
        return any(t.startswith(rel.rstrip("/") + "/") for t in TRACKED)
    return False

# --- documents that must state the current numbers --------------------------------
CANONICAL = [
    REPO / "README.md",
    REPO / "TerraTrace-PROJECT-BRIEF.md",
    ROOT / "README.md",
    ROOT / "docs" / "index.md",
    ROOT / "docs" / "VALIDATION.md",
    ROOT / "docs" / "PAPER.md",
    ROOT / "docs" / "FEATURES.md",
    REPO / "site" / "index.html",
    # the deck generator is prose too: every number it prints ends up in a published slide, and
    # "200 scalar outputs" sat in a shipped slide for a release because nothing audited this file.
    ROOT / "scripts" / "build_deck.js",
    ROOT / "scripts" / "build_submission_deck.js",
    ROOT / "scripts" / "make_cover.py",
    # this one publishes the mirror numbers (3600x3600, 12,960,000 values, a 360-byte delta) into a
    # page readers check, so it is prose in the same sense the deck generators are
    ROOT / "scripts" / "verify_earth_mirror.py",
]

# dated records: exempt from the count checks
HISTORICAL = {
    "CHANGELOG.md",
    "CLAIM-LEDGER.md",
    "RESULTS-v2.md",
    "RESULTS-v3.md",
    "REAL-EXAMPLE.md",
    "BENCHMARK-PROTOCOL.md",
    "BENCHMARK-PROTOCOL-v2.md",
    "BENCHMARK-PROTOCOL-v3.md",
    "BENCHMARK-PROTOCOL-v3-PROPOSAL.md",
}

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".claude", "artifacts", "data", "site-packages"}

# the frozen v3 verdicts, as checked against docs/RESULTS-v3.md
V3_VERDICTS = ("S — SUPPORTED", "V — NOT SUPPORTED", "R — SUPPORTED")

# Patterns that find a *stated* count in prose, with a label and the true value they must
# equal. Kept as raw strings so tests/test_doc_consistency.py can pin their behaviour.
COUNT_RES = {
    # (?<![\w.]) stops "python3 tests/…" from matching as "3 tests"
    # (?<!\u2192\s) exempts a progression: "Suite 583 \u2192 686 tests" is a dated record of what the
    # count *was*, and rewriting history to satisfy a count check would destroy the audit trail.
    "test count": r"(?<![\w.])(?<!\u2192\s)(\d+)\s+(?:offline\s+|fixture\s+|automated\s+)?tests?\b(?!\s+modules?\b)",
    "oracle count": r"(?<![\w.])(\d+)\s+(?:scientific-correctness\s+|validation\s+)?oracles?\b",
    # \b stops "COP30 product" from matching as "30 product"
    # one optional adjective is allowed ("15 cited sources", "14 catalogued products"): the old
    # pattern only matched the bare form, so a slide shipped saying "14 catalogued products" while
    # the registry held 15, and the guard that exists to catch exactly that did not fire.
    "source count": r"\b(\d+)[-\s](?:[\w'-]+\s+)?(?:source|product)s?\b",
    # the module and family counts drifted silently before these existed: "854 tests across 91
    # modules" was written when the tree had 92, and they were caught by a reader, not by CI.
    # (Numbers here are a dated quote about past drift, not a current count — do not update them.)
    # "884 fixtures" as a whole phrase, checked on its own. It is matched only as a PLURAL followed by
    # punctuation, a conjunction, or the end of a line, because "the 6 fixture tiles" is a different
    # thing entirely — the broader form that merely allowed `fixtures?` as a noun fired on exactly
    # that during testing. "884 fixtures and 51 oracles" is still matched; "884 fixtures with known
    # answers" is not, which is the deliberate side of the trade: under-coverage, never a false alarm.
    "fixture count": r"(?<![\w.])(\d+)\s+fixtures\b(?![-\s]+(?!(?:and|or)\b)[A-Za-z])",
    "module count": r"(?<![\w.])(\d+)\s+(?:test\s+)?modules?\b",
    "family count": r"(?<![\w.])(\d+)\s+(?:descriptor\s+)?families\b",
    "runner banner": r"passed=(\d+)\s",
}

# Counts that are only true as a range. Each entry is (pattern, label) and the stated number must
# fall inside the measured (min, max); the "roughly/around/~" is optional in the pattern because
# writers hedge half the time and a guard that only catches the unhedged form is a guard that
# misses the claim it was written for.
RANGE_RES = {
    "scalar count": r"(?<![\w.])(?:around\s+|roughly\s+|about\s+|~\s*)?(\d+)\s+scalar",
}


def _docs_files():
    """Every prose file we police (markdown + the hand-written HTML pages).

    Only *tracked* files are audited: an internal document that is deliberately git-ignored is
    not published, so a broken link inside it is not a defect a reader can ever meet.
    """
    for pat in ("**/*.md", "site/index.html"):
        for p in sorted(REPO.glob(pat)):
            if any(part in SKIP_DIRS for part in p.parts):
                continue
            if p.name in HISTORICAL:
                continue
            if TRACKED is not None and p.relative_to(REPO).as_posix() not in TRACKED:
                continue
            yield p


def _count_tests():
    """Module-level ``def test_*`` across tests/ — exactly what run_tests.py discovers."""
    n = 0
    for p in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        n += sum(1 for x in tree.body if isinstance(x, ast.FunctionDef) and x.name.startswith("test_"))
    return n


def _count_test_modules():
    """Modules that actually contribute tests, computed the same way the runner discovers them.

    A file count would include an empty or unittest-style module that the dependency-free runner
    silently skips, which is how a documented module count drifts away from reality.
    """
    n = 0
    for p in sorted((ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(p.read_text(encoding="utf-8"))
        if any(isinstance(x, ast.FunctionDef) and x.name.startswith("test_") for x in tree.body):
            n += 1
    return n


def _count_families():
    """Descriptor families, from the bank itself rather than from a document."""
    import numpy as np
    from terratrace import descriptors
    return len(descriptors.descriptor_bank(np.zeros((24, 24)) + 1.0))


def _count_scalars(sizes=(24, 32, 48, 64, 96, 128, 200)):
    """Leaf scalar values the bank emits, as a (min, max) over window sizes.

    This number is genuinely window-dependent (several families return a value per band or per
    window), so it can only be pinned as a range. It has drifted twice in the prose — an early
    revision said exactly 200 and the next said 210 — and a stated number that no code path can
    produce is a claim a reader cannot check. Measuring it here makes the range a fact.
    """
    import numpy as np
    from terratrace import descriptors

    def leaves(o):
        if isinstance(o, dict):
            return sum(leaves(v) for v in o.values())
        if isinstance(o, (list, tuple)):
            return sum(leaves(v) for v in o)
        return 1

    got = [leaves(descriptors.descriptor_bank(np.zeros((n, n)) + 1.0)) for n in sizes]
    return min(got), max(got)


def _count_oracles():
    tree = ast.parse((ROOT / "terratrace" / "validation.py").read_text(encoding="utf-8"))
    return sum(1 for x in tree.body if isinstance(x, ast.FunctionDef) and x.name.startswith("check_"))


def _count_sources():
    from terratrace import catalog
    return len(catalog.SOURCES)


def _probe(text):
    """The text as a regex should see it.

    Markup sits between a number and its noun in real prose — "**14** catalogued products",
    "**854** offline tests" — and every pattern here is written against plain words. Stripping the
    emphasis markers before matching (and reporting snippets from the stripped copy) closes a whole
    class of silent misses rather than special-casing each one.
    """
    return text.replace("**", "").replace("`", "")


def check_counts(problems):
    tests, oracles, sources = _count_tests(), _count_oracles(), _count_sources()
    modules, families = _count_test_modules(), _count_families()
    truth = {"test count": tests, "fixture count": tests, "oracle count": oracles,
             "source count": sources, "runner banner": tests, "module count": modules,
             "family count": families}
    pats = [(label, re.compile(rx), truth[label]) for label, rx in COUNT_RES.items()]
    for path in CANONICAL:
        if not path.exists():
            problems.append(f"counts: canonical document is missing: {path.relative_to(REPO)}")
            continue
        text = _probe(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(REPO)
        for label, pat, want in pats:
            for m in pat.finditer(text):
                got = int(m.group(1))
                if got != want:
                    problems.append(
                        f"counts: {rel} states {label} {got}, real value is {want} "
                        f"(…{text[max(0,m.start()-40):m.end()+15].strip()!r}…)"
                    )
    lo, hi = _count_scalars()
    rpats = [(label, re.compile(rx)) for label, rx in RANGE_RES.items()]
    for path in CANONICAL:
        if not path.exists():
            continue
        text = _probe(path.read_text(encoding="utf-8", errors="replace"))
        rel = path.relative_to(REPO)
        for label, pat in rpats:
            for m in pat.finditer(text):
                got = int(m.group(1))
                if not (lo <= got <= hi):
                    problems.append(
                        f"counts: {rel} states {label} {got}, outside the measured range "
                        f"{lo}-{hi} (...{text[max(0,m.start()-40):m.end()+15].strip()!r}...)"
                    )

    # The deck generators print their counts through a helper:
    #     stat(slide, x, y, w, "878", "offline tests across 94 modules, 0 failures", ACC)
    # The number and its noun sit in two *different* string arguments, so every pattern above —
    # each anchored on a number immediately followed by its noun — walks straight past them. That
    # is the same silent-miss shape as "**14** catalogued products", and a shipped slide carried a
    # wrong scalar count through exactly this hole. Match the call's argument shape instead.
    stat_call = re.compile(r'"(\d{1,4})"\s*,\s*"([^"]{0,140})"')
    nouns = [("module count", re.compile(r"\bmodules?\b", re.I)),
             ("test count", re.compile(r"\btests?\b", re.I)),
             ("oracle count", re.compile(r"\boracles?\b", re.I)),
             ("source count", re.compile(r"\b(?:source|product)s?\b", re.I)),
             ("family count", re.compile(r"\bfamilies\b", re.I))]
    for path in CANONICAL:
        if not path.exists() or path.suffix != ".js":
            continue
        raw = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(REPO)
        for m in stat_call.finditer(raw):
            got, label = int(m.group(1)), m.group(2)
            # the printed number labels whichever tracked noun appears first in its own caption —
            # including "scalar", so "40", "…families (~290 scalar values)" labels *families* and
            # the scalar range check must not capture it. (It did on the first run.)
            found = [(n.search(label).start(), title) for title, n in nouns if n.search(label)]
            s_pos = label.lower().find("scalar")
            if s_pos >= 0 and (not found or s_pos < min(found)[0]):
                if not (lo <= got <= hi):
                    problems.append(
                        f"counts: {rel} states scalar count {got} on a slide, outside the measured "
                        f"range {lo}-{hi} (...{label!r}...)"
                    )
                continue
            if found:
                title = min(found)[1]
                if got != truth[title]:
                    problems.append(
                        f"counts: {rel} states {title} {got} on a slide, real value is "
                        f"{truth[title]} (...{label!r}...)"
                    )
            # and a second count can hide inside the caption itself: "tests across 94 modules"
            for title, pat, want in pats:
                for mm in pat.finditer(_probe(label)):
                    if int(mm.group(1)) != want:
                        problems.append(
                            f"counts: {rel} states {title} {int(mm.group(1))} inside a slide "
                            f"caption, real value is {want} (...{label!r}...)"
                        )
    return tests, oracles, sources, modules, families, (lo, hi)


def check_versions(problems):
    src = (ROOT / "terratrace" / "__init__.py").read_text(encoding="utf-8")
    m = re.search(r'^__version__\s*=\s*["\']([^"\']+)["\']', src, re.M)
    if not m:
        problems.append("version: terratrace/__init__.py has no __version__")
        return
    ver = m.group(1)

    py = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    m2 = re.search(r'^\s*version\s*=\s*["\']([^"\']+)["\']', py, re.M)
    if not m2 or m2.group(1) != ver:
        problems.append(f"version: pyproject.toml says {m2.group(1) if m2 else '(none)'}, __version__ is {ver}")

    cff = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    m3 = re.search(r'^version:\s*(\S+)', cff, re.M)
    if not m3 or m3.group(1).strip('"') != ver:
        problems.append(f"version: CITATION.cff says {m3.group(1) if m3 else '(none)'}, __version__ is {ver}")
    return ver


def check_nav(problems):
    mk = ROOT / "mkdocs.yml"
    text = mk.read_text(encoding="utf-8")
    nav_docs = ROOT / "docs"
    # only the `nav:` block — not the top-level `docs_dir:` key, which also says "docs"
    m = re.search(r"^nav:\s*\n((?:[ \t]+[^\n]*\n|\s*\n)+)", text, re.M)
    nav_block = m.group(1) if m else ""
    entries = re.findall(r"^\s*-\s*[^:\n]+:\s*(\S+)\s*$", nav_block, re.M)
    listed = set()
    for rel in entries:
        target = nav_docs / rel
        listed.add(rel.replace("\\", "/"))
        if not target.exists():
            problems.append(f"nav: mkdocs.yml lists {rel!r}, which does not exist under docs/")
    for page in sorted(nav_docs.rglob("*.md")):
        rel = page.relative_to(nav_docs).as_posix()
        if rel not in listed:
            problems.append(f"nav: docs/{rel} exists but is not in mkdocs.yml nav (a reader cannot reach it)")


# The site is PUBLISHED from `site/`, so a URL is relative to that directory — GitHub Pages resolves
# /study/ to site/study/index.html with no rewrite table at all. An earlier revision resolved routes
# against the repository root instead, which only appeared to work because Vercel's rewrite table
# happened to spell out each route; the moment the links gained their canonical trailing slash (as
# GitHub Pages serves them) every one of them "broke". The site root is a fact about the deployment,
# so it is named here rather than inferred from a host's configuration.
SITE_ROOT = REPO / "site"


def resolve_site_route(route, routes=None, root=None):
    """Map a URL path from the site to the file that serves it. Returns a Path (maybe nonexistent).

    Host-neutral on purpose: a route named by a rewrite table resolves through that table, and
    anything else falls back to plain static-tree rules, which is what GitHub Pages implements.
    """
    routes = routes or {}
    root = SITE_ROOT if root is None else root
    for key in (route, route.rstrip("/"), route.rstrip("/") + "/"):
        if key in routes:
            return REPO / routes[key]
    cand = root / route.strip("/")
    if cand.is_dir():
        return cand / "index.html"
    if cand.suffix:
        return cand
    if (cand.parent / (cand.name + ".html")).exists():
        return cand.parent / (cand.name + ".html")
    return cand / "index.html"


def check_links(problems):
    """Relative Markdown links, and the site's internal HTML links + fragments.

    The second half matters because the deployed site routes through ``vercel.json``:
    ``/`` and ``/study`` and ``/viewer`` are rewrites, not directories, so a page can look
    fine in the repo and 404 in the browser. The rewrite table is read from
    ``vercel.json`` itself, so adding a page without wiring a route is a failure here.
    """
    n = 0
    for path in _docs_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r"\]\(([^)\s]+)\)", text):
            tgt = m.group(1)
            if "://" in tgt or tgt.startswith("#") or tgt.startswith("mailto:"):
                continue
            rel = tgt.split("#")[0]
            if not rel:
                continue
            n += 1
            target = path.parent / rel
            if not _readable(target):
                why = ("exists here but is NOT TRACKED, so a clone will not have it"
                       if target.exists() else "does not exist")
                problems.append(f"links: {path.relative_to(REPO)} -> {tgt!r} {why}")

    # --- the website ---------------------------------------------------------
    vercel = REPO / "vercel.json"
    routes, clean = {}, False
    if vercel.exists():
        cfg = vercel.read_text(encoding="utf-8")
        clean = '"cleanUrls": true' in cfg     # informational: resolution no longer depends on it
        for m in re.finditer(r'"source"\s*:\s*"([^"]+)"\s*,\s*"destination"\s*:\s*"([^"]+)"', cfg):
            routes[m.group(1)] = m.group(2).lstrip("/")


    pages = []
    for page in sorted(REPO.glob("site/**/*.html")):
        if TRACKED is not None and page.relative_to(REPO).as_posix() not in TRACKED:
            continue
        pages.append(page)
    for page in pages:
        text = page.read_text(encoding="utf-8", errors="replace")
        for m in re.finditer(r'href="([^"]+)"', text):
            href = m.group(1)
            if "://" in href or href.startswith("mailto:") or href.startswith("data:"):
                continue
            route, _, frag = href.partition("#")
            n += 1
            if not route:                       # same-page fragment
                ids = set(re.findall(r'id="([^"]+)"', text))
                if frag and frag not in ids:
                    problems.append(f"site: {page.name} -> {href!r} has no target id in that page")
                continue
            tgt = resolve_site_route(route, routes)
            if not _readable(tgt):
                problems.append(
                    f"site: {page.relative_to(REPO)} -> {href!r} resolves to "
                    f"{tgt.relative_to(REPO)} which a clone will not have (is the route wired?)")
            elif frag:
                ids = set(re.findall(r'id="([^"]+)"', tgt.read_text(encoding="utf-8", errors="replace")))
                if frag not in ids:
                    problems.append(
                        f"site: {page.relative_to(REPO)} -> {href!r} has no target id in {tgt.name}")
    return n


def check_claims(problems):
    """The v3 verdicts quoted in the live docs must match RESULTS-v3.md."""
    results = (ROOT / "docs" / "RESULTS-v3.md").read_text(encoding="utf-8")
    for v in V3_VERDICTS:
        if v not in results:
            problems.append(f"claims: RESULTS-v3.md no longer contains the frozen verdict {v!r}")
    # wherever the live docs state S/V/R, the pre-specification caveat must be present nearby
    for path in _docs_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        if "NOT SUPPORTED" in text and "volcanic" in text.lower():
            if "pre-specified" not in text and "pre-registered" not in text:
                problems.append(
                    f"claims: {path.relative_to(REPO)} states a v3 verdict without the "
                    f"pre-specification caveat"
                )


# "N independent lenses/axis sets" reads as independent replications of the same finding. The six
# lens sets each contain the core metrics and add to them, so they are correlated by construction and
# agreement between them is a robustness read, not confirmation. The wording drifted in once and is
# cheap to prevent, so it is a check rather than a note.
LENS_OVERCLAIM = re.compile(r"\b\w+\s+independent\s+(?:axis|lens|metric)", re.I)


def check_lens_wording(problems):
    for path in _docs_files():
        text = _probe(path.read_text(encoding="utf-8", errors="replace"))
        for m in LENS_OVERCLAIM.finditer(text):
            problems.append(
                f"claims: {path.relative_to(REPO)} calls lenses/axis sets "
                f"{m.group(0)!r} independent — they share the core metrics, so they are correlated "
                f"by construction and cannot confirm each other"
            )


def check_site_markup(problems):
    """Every tracked HTML page must be tag-balanced.

    A defect class the link check is blind to: a wrong number of closing tags still contains
    perfectly resolvable links, so it passes `check_links` and renders as a broken page. `site/` is
    the surface a judge actually opens, and it is edited by hand, so it is worth a parser.
    """
    from html.parser import HTMLParser

    void = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta",
            "param", "source", "track", "wbr"}

    class Balance(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.stack, self.errors = [], []

        def handle_starttag(self, tag, attrs):
            if tag not in void:
                self.stack.append((tag, self.getpos()[0]))

        def handle_endtag(self, tag):
            if tag in void:
                return
            if not self.stack:
                self.errors.append(f"</{tag}> on line {self.getpos()[0]} closes nothing")
                return
            top, line = self.stack.pop()
            if top != tag:
                self.errors.append(
                    f"</{tag}> on line {self.getpos()[0]} closes <{top}> opened on line {line}")

    n = 0
    for page in sorted(REPO.glob("site/**/*.html")):
        if TRACKED is not None and page.relative_to(REPO).as_posix() not in TRACKED:
            continue
        n += 1
        parser = Balance()
        parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        rel = page.relative_to(REPO)
        for e in parser.errors[:5]:
            problems.append(f"markup: {rel}: {e}")
        for tag, line in parser.stack[:5]:
            problems.append(f"markup: {rel}: <{tag}> opened on line {line} is never closed")
    return n


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    quiet = "--quiet" in argv
    problems = []
    tests, oracles, sources, modules, families, scalar_range = check_counts(problems)
    ver = check_versions(problems)
    check_nav(problems)
    n_links = check_links(problems)
    check_claims(problems)
    check_lens_wording(problems)
    n_pages = check_site_markup(problems)

    if not quiet:
        print(f"doc consistency: {tests} tests across {modules} modules, {oracles} oracles, "
              f"{sources} catalog sources, {families} descriptor families "
              f"({scalar_range[0]}-{scalar_range[1]} scalars), version {ver}, "
              f"{n_links} relative links, {n_pages} HTML pages, "
              f"{len(CANONICAL)} canonical documents")
    if problems:
        print(f"\n{len(problems)} documentation-consistency problem(s):")
        for p in problems:
            print(f"  - {p}")
        return 1
    if not quiet:
        print("OK: documentation is consistent with the code.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
