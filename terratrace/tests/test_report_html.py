"""report_html fixtures (dependency-free, assert-based).

Covers: self-contained HTML parity with the Markdown renderer's contract, XSS /
injection escaping, the conditional Uncertainty section, batch rendering, and
determinism. Mirrors the small synthetic batch used in tests/test_report.py so
it stays fast and offline.
"""
from terratrace import study, batch, report_html


def _small_batch_report():
    """A tiny synthetic cross-reference batch: 2 Mars references, 2 candidates,
    core mode only, small grids -- fast and offline (mirrors tests/test_report.py)."""
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


def test_study_report_is_selfcontained_html_with_core_contract():
    pkg = study.run_study()
    h = report_html.study_report_html(pkg)
    assert isinstance(h, str) and h.strip(), "report must be a non-empty string"
    # a complete HTML document
    assert h.lstrip().lower().startswith("<!doctype html")
    assert "<html" in h and "</html>" in h
    # inline style only, and NO external / CDN assets (fully self-contained, offline)
    assert "<style>" in h
    for needle in ("http://", "https://", "//cdn", "<link", "<script", "url("):
        assert needle not in h, needle
    # the result state is shown
    assert pkg["result_state"] in h
    # every declared decision axis appears
    for m in pkg["profile"]["metrics"]:
        assert m in h, m
    # the provenance hash is embedded
    assert pkg["package_hash"] in h
    # claim-firewall text + at least one prohibited claim reproduced verbatim
    assert "CLAIM-FIREWALL" in h
    assert any(claim in h for claim in pkg["prohibited_claims"])
    # at least one HTML table
    assert "<table" in h


def test_study_report_escapes_injected_markup():
    pkg = study.run_study()
    evil = "<script>alert(1)</script>"
    # inject into fields the renderer presents (eligibility reason + source label)
    uid = next(iter(pkg["eligibility"]))
    pkg["eligibility"][uid]["reason"] = evil
    pkg["profile"]["source_label"] = evil
    h = report_html.study_report_html(pkg)
    assert evil not in h                 # the raw <script> tag must not survive
    assert "&lt;script&gt;" in h         # it must appear escaped


def test_uncertainty_section_only_with_bootstrap():
    with_boot = report_html.study_report_html(study.run_study(n_boot=40))
    without = report_html.study_report_html(study.run_study())
    assert "<h2>Uncertainty</h2>" in with_boot
    assert "nondominated_freq" in with_boot
    assert "<h2>Uncertainty</h2>" not in without


def test_batch_report_html_has_consensus_and_candidates():
    rep = _small_batch_report()
    h = report_html.batch_report_html(rep)
    assert isinstance(h, str) and h.strip()
    assert h.lstrip().lower().startswith("<!doctype html")
    assert "<table" in h
    # both candidate ids are rendered
    assert "twin" in h and "rough" in h
    # the consensus shortlist is non-empty here and every member is rendered
    assert rep["consensus_shortlist"], "expected a non-empty consensus shortlist"
    assert "twin" in rep["consensus_shortlist"]
    for c in rep["consensus_shortlist"]:
        assert c in h
    # the provenance hash is embedded
    assert rep["package_hash"] in h


def test_report_html_is_deterministic():
    pkg = study.run_study(n_boot=40)
    assert report_html.study_report_html(pkg) == report_html.study_report_html(pkg)
    rep = _small_batch_report()
    assert report_html.batch_report_html(rep) == report_html.batch_report_html(rep)


def test_report_html_renders_feature_uncertainty_and_previews_when_present():
    from terratrace import synthetic
    n, L = 64, 25.0
    raw = {"mars_reference": synthetic.plane((n, n), 0.12, 0.05) + synthetic.rough_field((n, n), 0.6, 1),
           "earth_close": synthetic.plane((n, n), 0.11, 0.06) + synthetic.rough_field((n, n), 0.65, 2)}
    rights = {k: "verified_allowed" for k in raw}
    pkg = study.compare_units(raw, rights, L, target_support_m=100.0,
                              vertical_accuracy={"mars_reference": 3.0, "earth_close": 4.0},
                              previews=True)
    h = report_html.study_report_html(pkg)
    assert "Measurement uncertainty" in h and "Terrain previews" in h
    assert "data:image/png;base64," in h            # self-contained inline preview
    # absent for a plain study (no new sections leak in)
    assert "Measurement uncertainty" not in report_html.study_report_html(study.run_study())
