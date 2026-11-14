"""The offline evidence page: it must be built FROM the atlas, and it must work with the network off.

Two properties, and the second is the one that gets quietly lost.

The first is provenance: every number on the page has to come from
`artifacts/discovery_atlas/discovery_atlas.json`, so a reader can check the page against the record
it claims to describe. The tests below recompute the page's headline numbers from the atlas JSON
rather than hardcoding them, which is the same discipline the page itself is held to.

The second is that it is genuinely offline: no fetch, no external stylesheet, no CDN, no API key,
no browser storage. A page that needs a request to render has not demonstrated anything on a laptop
with the network off, which is the condition the main demonstration has to satisfy. `localStorage`
is singled out because it is the one that looks like it works -- it is silently unavailable in a
sandboxed preview, and a page that depends on it fails somewhere the author never sees.
"""
import json
import pathlib
import re
import sys

_HERE = pathlib.Path(__file__).resolve().parent
_ROOT = _HERE.parent
_REPO = _ROOT.parent
sys.path.insert(0, str(_ROOT))
sys.path.insert(0, str(_HERE))          # harness.py lives HERE, not in the package

from harness import require                                        # noqa: E402

ATLAS = _ROOT / "artifacts" / "discovery_atlas" / "discovery_atlas.json"
STRESS = _ROOT / "artifacts" / "lunar_adversarial" / "lunar_adversarial.json"
PAGE = _REPO / "site" / "atlas" / "index.html"


def _atlas():
    require(ATLAS.exists(), "the atlas record is absent, so the page cannot be checked against it")
    return json.loads(ATLAS.read_text(encoding="utf-8"))


def _page():
    require(PAGE.exists(), "site/atlas/index.html was not built; run scripts/build_atlas_page.py")
    return PAGE.read_text(encoding="utf-8")


# ------------------------------------------------------------------ it is offline, for real

def test_the_page_loads_nothing_from_outside_itself():
    h = _page()
    for bad in ("<script src=", "<link rel=\"stylesheet\"", "@import", "fetch(", "XMLHttpRequest",
                "navigator.sendBeacon", "localStorage", "sessionStorage", "indexedDB"):
        assert bad not in h, (
            f"the page contains {bad!r}. The main demonstration has to render with the network off "
            f"and no browser storage available, so nothing may be loaded or stored at runtime.")
    for url in re.findall(r"https?://[^\s\"'<>)]+", h):
        assert "github.com/pal-123456789" in url or "terratrace.fit" in url, (
            f"the page references an external URL it might depend on: {url}")


def test_the_page_carries_its_own_data_rather_than_fetching_it():
    """The windows have to be IN the page, or the tables render empty offline."""
    h, a = _page(), _atlas()
    for w in a["windows"][:5]:
        assert str(w["reference"]) in h, f"{w['reference']} is not in the page"
    assert h.count("<table") >= 5, "the page has fewer tables than it has sections"


# ------------------------------------------------------------------ it is built from the atlas

def test_the_headline_numbers_are_the_atlas_numbers():
    h, a = _page(), _atlas()
    hl = a["headline"]
    assert f"definite at {hl['ranking_definite_cells']} / {hl['ranking_cells']}" in h
    assert f"not established, at all {hl['ranking_cells']}" in h
    assert f"{hl['stress_stable_of_counted'][1]} perturbations were declared" in h
    assert f"{hl['stress_stable_of_counted'][0]} of {hl['stress_stable_of_counted'][1]}" in h


def test_the_decision_matrix_has_one_row_per_cell_and_agrees_with_the_atlas():
    h, a = _page(), _atlas()
    assert h.count('<td class="bad">NOT_ESTABLISHED</td>') == sum(
        1 for x in a["adequacy"].values() if x["state"] == "NOT_ESTABLISHED")
    for key in a["ranking"]:
        assert f'<td class="m">{key}</td>' in h, f"the decision matrix omits {key}"
    for r in a["ranking"].values():
        assert r["recommended_unit"] in h
    for suf in a["sufficiency"].values():
        assert suf["state"].lower() in h


def test_every_reconciliation_is_on_the_page_with_the_records_it_holds_together():
    h, a = _page(), _atlas()
    for r in a["reconciliations"]:
        assert r["check"] in h, f"the page omits the reconciliation {r['check']}"
        assert r["where"] in h or r["where"].split(" <-> ")[0] in h, (
            f"{r['check']} is on the page without the records it holds together")


def test_the_page_names_the_record_it_was_built_from():
    h = _page()
    assert "artifacts/discovery_atlas/discovery_atlas.json" in h
    assert re.search(r"sha256 <code>[0-9a-f]{16}", h), (
        "the page must print the source record's hash prefix, so a reader can tell whether the page "
        "matches the record it describes")


# ------------------------------------------------------------------ the stability map

def test_the_stability_map_is_complete_and_counts_what_it_claims():
    """Recomputed from the stress record, not read off the page: the map's job is to be complete."""
    h = _page()
    stress = json.loads(STRESS.read_text(encoding="utf-8"))
    counted = [p for p in stress["perturbations"] if p["counted"]]
    grid = h[h.index('class="map"'):h.index('class="legend"')]
    n_unchanged = grid.count('class="st"')
    n_reversed = grid.count('class="rv"')
    n_na = grid.count('class="na"')
    n_cells = 6 * 3
    assert n_unchanged + n_reversed + n_na == len(counted) * n_cells, (
        "the map does not cover every cell against every counted perturbation, so a reader cannot "
        "tell a pass from a gap")
    expected_reversed = sum(len(p["changed"]) for p in counted)
    assert n_reversed == expected_reversed, (
        f"the map draws {n_reversed} reversals where the record has {expected_reversed}")
    single = [p for p in counted if p["n_cells"] == 6]
    assert n_na == len(single) * (n_cells - 6), (
        "the single-support perturbations must be drawn as NOT EVALUATED on the supports they never "
        "ran -- counting a coverage gap as a pass is the mistake the scorer itself made once")


def test_the_reversing_conditions_are_named_and_not_buried():
    h, a = _page(), _atlas()
    for lab in a["adversarial"]["reversing"]:
        assert lab in h, f"the reversing condition {lab} is not named on the page"


# ------------------------------------------------------------------ the firewall

def test_the_page_states_the_firewall_and_awards_nothing():
    h = _page()
    low = h.lower()
    assert "no traversability" in low and "mission-readiness claim" in low
    assert "no composite analog score" in low
    # a score would show up as a column header or a prominent single number
    heads = re.findall(r"<th[^>]*>(.*?)</th>", h, re.S)
    assert not any(k in hd.lower() for hd in heads for k in ("score", "rating", "grade")), (
        f"a score-like column header appears: {heads}")


def test_the_page_does_not_claim_any_test_count():
    """The page is about evidence for a terrain relationship, not about the test suite.

    A test count on a results page invites exactly the inference this project refuses -- that the
    number of checks is evidence for the finding. Easy to add by accident when quoting the atlas.
    """
    h = _page()
    assert not re.search(r"\b\d+\s+(?:offline\s+)?tests?\b", h), (
        "the evidence page quotes a test count; a check count is not evidence of a scientific result")
