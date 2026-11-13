"""Archival guards for the v3 benchmark.

These tests exist because of a real defect and a real hazard.

The defect: the project's presentation of the v3 resolution-robustness result listed
11 unchanged, 3 membership-changed and 0 reversed -- fourteen cells presented as the
whole of a fifteen-cell experiment. The one *destabilised* cell had been dropped by
omission. Nothing failed, because a breakdown that silently loses a category still
reads as a breakdown. The cell is `mars_solis @ 1500 m`, where matching the footprint
turns a single recommendation into a TIE; it is a meaningful result and it belongs on
the page, not out of it.

The hazard: the config that produced the result carries a stale `NOT YET FROZEN`
header and a checksum that no longer matches the file at HEAD (one comment was
corrected afterwards). Both are explained in docs/V3-ARCHIVAL-CLARIFICATION.md, and
neither should be "tidied" by a later edit.

So: the counts must sum, every non-zero category must be present wherever a breakdown
is stated, the published artifact must be the one in the repository, and the config's
parameters must still be the frozen parameters. Standard library only -- this module
runs in CI where only NumPy is installed.
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import re
import subprocess

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent                      # .../terratrace
REPO = ROOT.parent                      # repository root

BUNDLE = ROOT / "artifacts" / "mf_panel_v3" / "matched_panel_v3_real.json"
CONFIG = ROOT / "config" / "matched_footprint_v3.yml"
RESULTS = ROOT / "docs" / "RESULTS-v3.md"

# --- frozen values, all recoverable from the repository ---------------------------
# The bundle as produced by the 2026-11-05 20:06:54 IST run.
BUNDLE_SHA = "4a4922e3396c3531641066a4f8fa8334590ec22f16ba5df69cb11339b689b695"
# The shipped config, and its parameters with comments removed. See the archival page:
# the config that produced the result hashes to 70eeafd4... and differs from this one
# only in the Nevada Basin sigma comment, so the parameter digest is identical.
CONFIG_SHA = "985350769cc7d347a4d524b11cd47da04b3e36948e1eff7f40e3eaccbd324f0c"
CONFIG_PARAM_SHA = "ff3add2ce5add53f37ea75b175d3c580d7aeb464bcca4886ff46509e1ead7560"
CONFIG_SHA_AT_RESULT_COMMIT = "70eeafd4160f11502a35c898dfc47daef4f7087dd307311adbd9a8c9c2aa236de4f"

TOTAL_CELLS = 15
CLASSES = ("unchanged", "stabilised", "destabilised", "reversed", "membership_changed", "error")

# surfaces that state the v3 result to a reader
SURFACES = [
    ROOT / "docs" / "RESULTS-v3.md",
    ROOT / "docs" / "V3-ARCHIVAL-CLARIFICATION.md",
    ROOT / "README.md",
    REPO / "README.md",
    REPO / "site" / "index.html",
    REPO / "site" / "study" / "index.html",
    ROOT / "scripts" / "build_deck.js",
]


def _sha(text_or_bytes) -> str:
    b = text_or_bytes.encode("utf-8") if isinstance(text_or_bytes, str) else text_or_bytes
    return hashlib.sha256(b).hexdigest()


def _bundle():
    return json.loads(BUNDLE.read_text(encoding="utf-8"))


def _counts():
    return _bundle()["hypotheses"]["R"]["counts"]


def _rows():
    return _bundle()["hypotheses"]["R"]["evidence"]["rows"]


def _param_digest(path) -> str:
    """Hash of the config's parameters: comments and blank lines removed.

    A comment-only edit must NOT look like a parameter change -- that is precisely what
    happened to this config after the run, and it was legitimate. A change to any value
    must fail loudly.
    """
    keep = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.split(" #", 1)[0].strip()
        if not line or line.startswith("#"):
            continue
        keep.append(line)
    return _sha("\n".join(keep))


# --- the artifact ----------------------------------------------------------------

def test_the_v3_bundle_is_the_one_that_was_run():
    assert BUNDLE.exists(), f"the v3 result bundle is missing: {BUNDLE}"
    assert _sha(BUNDLE.read_bytes()) == BUNDLE_SHA, (
        "the v3 result bundle has changed since the run it documents. If a legitimate "
        "correction changed a result, version it and record why -- do not edit in place.")


def test_the_v3_bundle_is_published_not_just_present():
    """A checksum for a file a reader cannot obtain is not evidence."""
    try:
        tracked = subprocess.run(["git", "-C", str(REPO), "ls-files", "--error-unmatch",
                                  str(BUNDLE.relative_to(REPO))],
                                 capture_output=True, text=True).returncode == 0
    except Exception:
        return                          # no git (exported tarball) -- nothing to assert
    assert tracked, ("the v3 result bundle is not tracked by git, so the checksum "
                     "published in docs/RESULTS-v3.md points at a file no reader has")


def test_v3_counts_sum_to_the_confirmatory_cell_total():
    counts, rows = _counts(), _rows()
    missing = [c for c in CLASSES if c not in counts]
    assert not missing, f"classification counts are missing categories: {missing}"
    assert sum(counts.values()) == len(rows) == TOTAL_CELLS, (
        f"the six classification counts sum to {sum(counts.values())} but there are "
        f"{len(rows)} confirmatory cells")


def test_the_destabilised_cell_is_present_and_named():
    """The cell that the presentation dropped. It must be counted and identifiable."""
    assert _counts()["destabilised"] == 1
    dest = [r for r in _rows() if r["change"] == "destabilised"]
    assert len(dest) == 1
    assert dest[0]["reference"] == "mars_solis" and dest[0]["status"] == "confirmatory"
    assert {"deccan_traps", "llano_estacado"} <= {c.replace("earth_", "") for c in dest[0]["matched_layer1"]}, (
        "the destabilised cell should show the layer-1 set gaining a member")


def test_the_published_breakdown_equals_the_artifact():
    """Positional, so markdown emphasis cannot make a wrong number read as right."""
    order = ["unchanged", "stabilised", "destabilised", "reversed", "membership_changed", "error"]
    counts = _counts()
    want = [counts[c] for c in order]
    rows = _table_rows(RESULTS.read_text(encoding="utf-8"))
    for i, row in enumerate(rows):
        words = " ".join(row).lower()
        if sum(1 for c in CLASSES if c in words) < 6:
            continue
        for follow in rows[i + 1:i + 4]:
            cells = [re.sub(r"[^0-9]", "", c) for c in follow]
            if len(cells) == 6 and all(c != "" for c in cells):
                got = [int(c) for c in cells]
                assert got == want, (
                    f"docs/RESULTS-v3.md states {got} for "
                    f"{order}, the artifact says {want}")
                return
    raise AssertionError("docs/RESULTS-v3.md has no six-class breakdown table")


# --- the arithmetic guard for the class of defect this file was written for -------

_CLASS_RE = re.compile(
    r"(\d+)\s+(unchanged|stabilised|destabilised|reversed|membership[-_ ]changed)", re.I)


def _inline_groups(text):
    """Runs of (number, class) pairs close enough together to be one breakdown."""
    groups, cur, last = [], [], None
    for m in _CLASS_RE.finditer(text):
        if last is not None and m.start() - last > 90:
            if len(cur) >= 2:
                groups.append(cur)
            cur = []
        cur.append((int(m.group(1)), re.sub(r"[-_ ]", " ", m.group(2).lower())))
        last = m.end()
    if len(cur) >= 2:
        groups.append(cur)
    return groups


def _table_rows(text):
    rows = []
    for m in re.finditer(r"(?m)^\|(.+)\|\s*$", text):
        rows.append([c.strip() for c in m.group(1).split("|")])
    for m in re.finditer(r"<tr[^>]*>(.*?)</tr>", text, re.S | re.I):
        rows.append([re.sub(r"<[^>]+>", "", c).strip()
                     for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", m.group(1), re.S | re.I)])
    return rows


def _required():
    """Categories a breakdown may not omit: the ones that actually occur."""
    return {c.replace("_", " ") for c, n in _counts().items() if n}


def _check_surface(path, problems):
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8", errors="replace")
    rel = path.relative_to(REPO)

    for group in _inline_groups(text):
        total = sum(n for n, _ in group)
        # A breakdown of this experiment is always anchored on its majority class: "unchanged"
        # holds 11 of the 15 cells, so any full accounting names it. A group that does not is a
        # summary of one aspect ("no reversals; 1 destabilised; 3 membership-changed"), not a
        # claim about the whole -- and must not be summed as though it were.
        if total == TOTAL_CELLS or len(group) < 3 or not any(c == "unchanged" for _, c in group):
            continue
        problems.append(
            f"{rel}: states a {len(group)}-way breakdown summing to {total}, not "
            f"{TOTAL_CELLS} -- a category has been dropped or double-counted")
    # a breakdown that names the classes but omits an occurring one is wrong even if
    # its arithmetic happens to work out
    for group in _inline_groups(text):
        named = {c for _, c in group}
        if len(group) >= 3 and _required() - named and sum(n for n, _ in group) < TOTAL_CELLS:
            problems.append(f"{rel}: breakdown omits {sorted(_required() - named)}")

    # tables: a row of numbers under a header naming the classes must sum to the total
    rows = _table_rows(text)
    for i, row in enumerate(rows):
        words = " ".join(row).lower()
        if sum(1 for c in CLASSES if c.replace("_", " ") in words.replace("_", " ")) < 4:
            continue
        for follow in rows[i + 1:i + 4]:
            cells = [c for c in follow if re.fullmatch(r"\d+", c)]
            if len(cells) >= 6:
                got = sum(int(c) for c in cells)
                if got != TOTAL_CELLS:
                    problems.append(f"{rel}: classification table sums to {got}, not {TOTAL_CELLS}")
                break


def test_no_public_surface_states_a_breakdown_that_does_not_sum():
    problems = []
    for path in SURFACES:
        _check_surface(path, problems)
    assert not problems, "v3 breakdown inconsistency:\n  - " + "\n  - ".join(problems)


# --- provenance guards -----------------------------------------------------------

def test_the_v3_config_parameters_are_still_frozen():
    assert _sha(CONFIG.read_bytes()) == CONFIG_SHA, (
        "the v3 config file changed. If you changed a parameter, you have invalidated the "
        "v3 result and must version it as a new experiment -- see "
        "docs/V3-ARCHIVAL-CLARIFICATION.md.")
    assert _param_digest(CONFIG) == CONFIG_PARAM_SHA, "the v3 config's parameters changed"


def test_the_v3_verdict_is_never_quoted_without_its_pre_specification_caveat():
    for path in SURFACES:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "NOT SUPPORTED" in text and "volcanic" in text.lower():
            assert "pre-specified" in text or "pre-registered" in text, (
                f"{path.relative_to(REPO)} quotes the v3 verdicts without the "
                f"pre-specification caveat")


def test_the_core_lens_scope_is_recorded_where_the_verdicts_are():
    """The confirmatory result is core-lens. That must be stated, not implied."""
    assert _bundle()["hypotheses"]["R"].get("counts") is not None
    text = RESULTS.read_text(encoding="utf-8")
    assert "decision_metrics" in text and "core" in text, (
        "docs/RESULTS-v3.md must state that the confirmatory experiment used the core lens")
