"""Publication-grade report module fixtures (dependency-free, assert-based)."""
from terratrace import study, batch, report


def _small_batch_report():
    """A tiny synthetic cross-reference batch: 2 Mars references, 2 candidates,
    core mode only, small grids -- fast and offline (mirrors tests/test_batch.py)."""
    from terratrace import synthetic
    n, L = 32, 10.0
    base = synthetic.plane((n, n), slope_x=0.02, dx=L)
    units = {
        "mars_a": base + synthetic.rough_field((n, n), 0.8, seed=1),
        "mars_b": (synthetic.plane((n, n), slope_x=0.025, dx=L)
                   + synthetic.rough_field((n, n), 0.85, seed=11)),
        "twin": base + synthetic.rough_field((n, n), 0.85, seed=2),
        "rough": base + synthetic.rough_field((n, n), 4.0, seed=3),
    }
    return batch.run_batch(units, ["mars_a", "mars_b"], ["twin", "rough"], L,
                           target_support_m=L, decision_modes=("core",))


def test_study_report_is_nonempty_markdown_with_core_contract():
    pkg = study.run_study()
    md = report.study_report_md(pkg)
    assert isinstance(md, str) and md.strip(), "report must be a non-empty string"
    # scope / claim-firewall marker is present
    assert "CLAIM-FIREWALL" in md
    # at least one prohibited claim is reproduced verbatim
    assert any(claim in md for claim in pkg["prohibited_claims"])
    # result state (and the recommendation, when there is one)
    assert pkg["result_state"] in md
    if pkg["recommended_unit"]:
        assert pkg["recommended_unit"] in md
    # every declared decision axis appears
    for m in pkg["profile"]["metrics"]:
        assert m in md, m
    # provenance hash is embedded
    assert pkg["package_hash"] in md
    # the document contains at least one Markdown table
    assert any(line.startswith("|") for line in md.splitlines())


def test_study_report_uncertainty_section_only_with_bootstrap():
    with_boot = report.study_report_md(study.run_study(n_boot=40))
    assert "Uncertainty" in with_boot
    assert "nondominated" in with_boot
    without = report.study_report_md(study.run_study())
    assert "Uncertainty" not in without


def test_batch_report_contains_consensus_and_candidates():
    rep = _small_batch_report()
    md = report.batch_report_md(rep)
    assert isinstance(md, str) and md.strip()
    # both candidate ids are rendered
    assert "twin" in md and "rough" in md
    # the consensus shortlist is non-empty here and every member is rendered
    assert rep["consensus_shortlist"], "expected a non-empty consensus shortlist"
    assert "twin" in rep["consensus_shortlist"]
    for c in rep["consensus_shortlist"]:
        assert c in md


def test_report_is_deterministic():
    pkg = study.run_study(n_boot=40)
    assert report.study_report_md(pkg) == report.study_report_md(pkg)
    rep = _small_batch_report()
    assert report.batch_report_md(rep) == report.batch_report_md(rep)
