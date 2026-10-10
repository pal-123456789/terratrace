"""Per-candidate site dossier fixtures (dependency-free, assert-based)."""
from terratrace import dossier, study

# One study run reused across the no-bootstrap tests, plus one bootstrapped run
# (kept small) -- computed once at import so the suite stays fast.
_PKG = study.run_study()
_PKG_BOOT = study.run_study(n_boot=40)


def test_recommended_unit_dossier_is_complete():
    pkg = _PKG
    rec = pkg["recommended_unit"]
    assert rec, "synthetic study should isolate a single recommendation"
    d = dossier.candidate_dossier(pkg, rec)
    assert d["unit"] == rec
    assert d["is_recommended"] is True
    assert d["eligible"] is True
    assert d["distances"], "recommended unit must have non-empty distances"
    # distances carry exactly the declared decision axes
    assert set(d["distances"]) == set(pkg["profile"]["metrics"])
    assert d["target_body"] == pkg["profile"]["target_body"]
    assert d["package_hash"] and d["package_hash"] == pkg["package_hash"]


def test_ineligible_unit_dossier_is_blocked_without_error():
    pkg = _PKG
    assert pkg["eligibility"]["earth_blocked"]["eligible"] is False
    d = dossier.candidate_dossier(pkg, "earth_blocked")  # must not raise
    assert d["eligible"] is False
    assert d["eligibility_reason"], "an ineligible unit must carry a reason"
    assert d["distances"] == {}
    assert d["frontier_layer"] is None
    assert d["uncertainty"] is None
    assert d["is_recommended"] is False


def test_bootstrap_unit_dossier_has_uncertainty():
    pkg = _PKG_BOOT
    rec = pkg["recommended_unit"]
    assert rec
    d = dossier.candidate_dossier(pkg, rec)
    assert isinstance(d["uncertainty"], dict)
    assert "nondominated_freq" in d["uncertainty"]
    assert d["uncertainty"]["nondominated_freq"] is not None
    # a run without a bootstrap leaves uncertainty absent
    assert dossier.candidate_dossier(_PKG, rec)["uncertainty"] is None


def test_dossier_md_renders_unit_metrics_and_verdict():
    pkg = _PKG
    rec = pkg["recommended_unit"]
    md = dossier.dossier_md(pkg, rec)
    assert isinstance(md, str) and md.strip(), "dossier must be a non-empty string"
    assert rec in md, "the unit id must appear"
    for m in pkg["profile"]["metrics"]:
        assert m in md, m
    assert "recommend" in md.lower(), "a verdict word must appear"
    assert any(line.startswith("|") for line in md.splitlines()), "needs a table"


def test_all_dossiers_covers_eligibility_and_unknown_raises():
    pkg = _PKG
    alld = dossier.all_dossiers(pkg)
    assert set(alld) == set(pkg["eligibility"])
    assert len(alld) == len(pkg["eligibility"])
    for uid, d in alld.items():
        assert d["unit"] == uid
    # a truly-unknown id (in neither baseline_vectors nor eligibility) raises
    bad = "no_such_unit_xyz"
    assert bad not in pkg["eligibility"] and bad not in pkg["baseline_vectors"]
    raised = False
    try:
        dossier.candidate_dossier(pkg, bad)
    except (KeyError, ValueError):
        raised = True
    assert raised, "an unknown unit must raise KeyError/ValueError"
