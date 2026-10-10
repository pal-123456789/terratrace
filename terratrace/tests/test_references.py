"""Data-sources citation / credits bundle (references module)."""
from terratrace import references, catalog


def test_references_for_covers_whole_catalog_with_documented_keys():
    recs = references.references_for()
    assert isinstance(recs, list)
    assert len(recs) == len(catalog.all_ids())          # one record per source
    keys = set(references.REFERENCE_FIELDS)
    assert keys == {"id", "body", "provider", "product", "citation",
                    "license", "endpoint", "native_resolution_m"}
    all_ids = set(catalog.all_ids())
    seen = set()
    for r in recs:
        assert set(r) == keys                           # exactly the documented keys
        assert r["id"] in all_ids
        seen.add(r["id"])
        # endpoint is sourced from the catalog entry's access block
        assert r["endpoint"] == catalog.get(r["id"])["access"].get("endpoint")
    assert seen == all_ids


def test_references_for_is_sorted_deterministically():
    recs = references.references_for()
    keyed = [(references._body_sort_key(r["body"]), r["id"]) for r in recs]
    assert keyed == sorted(keyed)                        # sorted by (body-order, id)
    assert [r["id"] for r in recs] == [r["id"] for r in references.references_for()]


def test_references_md_has_recognisable_citations_and_licences():
    md = references.references_md()
    assert isinstance(md, str) and md.strip()
    assert "Copernicus" in md          # Earth (ESA Copernicus)
    assert "MOLA" in md                # Mars (MGS MOLA)
    assert "LOLA" in md                # Moon (LRO LOLA)
    assert ("public" in md.lower()) or ("attribution" in md.lower())   # a licence word
    assert "term" in md.lower()        # header states "used under its own terms"


def test_references_md_mentions_every_body_present():
    bodies = {r["body"] for r in references.references_for()}
    assert {"earth", "mars", "moon", "mercury", "ceres"} <= bodies
    md = references.references_md()
    for b in bodies:
        assert references._body_title(b) in md           # each body is named


def test_references_for_single_source_returns_its_real_citation():
    recs = references.references_for(["earth_cop30"])
    assert len(recs) == 1
    r = recs[0]
    assert r["id"] == "earth_cop30"
    assert r["body"] == "earth"
    assert r["citation"] == catalog.get("earth_cop30")["citation"]
    assert "Copernicus" in r["citation"]


def test_used_source_ids_and_credits_on_study_package():
    from terratrace import study
    pkg = study.run_study()
    ids = references.used_source_ids(pkg)                 # no exception
    assert isinstance(ids, list)
    for sid in ids:                                       # every id is a real source
        assert sid in catalog.all_ids()
    credits = references.credits_for_package(pkg)
    assert isinstance(credits, str) and credits.strip()   # non-empty


def test_used_source_ids_real_label_returns_target_and_candidate_bodies():
    # A non-synthetic package must at least credit the target body's catalog sources,
    # and detect an Earth candidate unit alongside the Mars reference.
    pkg = {"profile": {"target_body": "mars", "source_label": "real_dem_aeqd"},
           "unit_metadata": {"mars_reference": {}, "earth_close": {}}}
    ids = references.used_source_ids(pkg)
    assert ids                                            # non-empty
    assert {s["id"] for s in catalog.by_body("mars")} <= set(ids)   # target body
    assert {s["id"] for s in catalog.by_body("earth")} <= set(ids)  # candidate body
    assert ids == sorted(ids)                             # deterministic order


def test_used_source_ids_synthetic_and_malformed_return_empty():
    assert references.used_source_ids(
        {"profile": {"target_body": "mars", "source_label": "synthetic"}}) == []
    assert references.used_source_ids({}) == []
    assert references.used_source_ids(None) == []


def test_credits_for_package_falls_back_to_full_catalog_with_lock_note():
    # synthetic -> used_source_ids == [] -> full catalog + a sources.lock.yml note
    md = references.credits_for_package(
        {"profile": {"target_body": "mars", "source_label": "synthetic"}})
    assert isinstance(md, str) and md.strip()
    assert "sources.lock" in md
    assert "Copernicus" in md and "MOLA" in md            # whole catalog rendered


def test_references_md_is_deterministic():
    assert references.references_md() == references.references_md()
    pick = ["earth_cop30", "mars_mola_megdr"]
    assert references.references_md(pick) == references.references_md(pick)
