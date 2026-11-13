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

1. **COUNTS**  — the canonical documents state the real test / oracle / catalog-source
   counts, computed here from the source.
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
    REPO / "site" / "index.html",
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
    "test count": r"(?<![\w.])(\d+)\s+(?:offline\s+|fixture\s+)?tests?\b",
    "oracle count": r"(?<![\w.])(\d+)\s+(?:scientific-correctness\s+|validation\s+)?oracles?\b",
    # \b stops "COP30 product" from matching as "30 product"
    "source count": r"\b(\d+)[-\s](?:source|product)s?\b",
    "runner banner": r"passed=(\d+)\s",
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


def _count_oracles():
    tree = ast.parse((ROOT / "terratrace" / "validation.py").read_text(encoding="utf-8"))
    return sum(1 for x in tree.body if isinstance(x, ast.FunctionDef) and x.name.startswith("check_"))


def _count_sources():
    from terratrace import catalog
    return len(catalog.SOURCES)


def check_counts(problems):
    tests, oracles, sources = _count_tests(), _count_oracles(), _count_sources()
    pats = [
        (label, re.compile(rx), {"test count": tests, "oracle count": oracles,
                                 "source count": sources, "runner banner": tests}[label])
        for label, rx in COUNT_RES.items()
    ]
    for path in CANONICAL:
        if not path.exists():
            problems.append(f"counts: canonical document is missing: {path.relative_to(REPO)}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        rel = path.relative_to(REPO)
        for label, pat, want in pats:
            for m in pat.finditer(text):
                got = int(m.group(1))
                if got != want:
                    problems.append(
                        f"counts: {rel} states {label} {got}, real value is {want} "
                        f"(…{text[max(0,m.start()-40):m.end()+15].strip()!r}…)"
                    )
    return tests, oracles, sources


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
        clean = '"cleanUrls": true' in cfg
        for m in re.finditer(r'"source"\s*:\s*"([^"]+)"\s*,\s*"destination"\s*:\s*"([^"]+)"', cfg):
            routes[m.group(1)] = m.group(2).lstrip("/")

    def _target(route):
        if route in routes:
            return REPO / routes[route]
        cand = REPO / route.lstrip("/")
        if cand.is_dir():
            return cand / "index.html"
        if cand.suffix:
            return cand
        if clean and (cand.parent / (cand.name + ".html")).exists():
            return cand.parent / (cand.name + ".html")
        return cand / "index.html"

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
            tgt = _target(route)
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


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    quiet = "--quiet" in argv
    problems = []
    tests, oracles, sources = check_counts(problems)
    ver = check_versions(problems)
    check_nav(problems)
    n_links = check_links(problems)
    check_claims(problems)

    if not quiet:
        print(f"doc consistency: {tests} tests, {oracles} oracles, {sources} catalog sources, "
              f"version {ver}, {n_links} relative links, {len(CANONICAL)} canonical documents")
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
