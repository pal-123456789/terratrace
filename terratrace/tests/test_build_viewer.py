"""build_viewer fixtures, including an injection-escaping regression."""
from terratrace import study, build_viewer


def test_build_html_basic():
    pkg = study.run_study()
    h = build_viewer.build_html(pkg)
    assert "<!doctype html>" in h
    assert pkg["result_state"] in h
    assert pkg["package_hash"] in h


def test_no_bootstrap_section_without_bootstrap():
    assert build_viewer._boot_section(study.run_study()) == ""
    assert "UNCERTAINTY (BOOTSTRAP" in build_viewer._boot_section(study.run_study(n_boot=40))


def test_body_badge_and_decision_matrix():
    pkg = study.run_study()
    h = build_viewer.build_html(pkg)
    # target-body badge (profile.target_body == "mars" -> "MARS")
    assert pkg["profile"]["target_body"].upper() in h
    assert "MARS" in h
    # decision matrix section carrying every decision-axis metric name
    assert "DECISION MATRIX" in h
    for metric in pkg["profile"]["metrics"]:
        assert metric in h
    # the "no composite score" honesty note and provenance are preserved
    assert "composite" in h
    assert pkg["package_hash"] in h


def test_uncertainty_and_frontier_panels():
    pkg = study.run_study(n_boot=40)
    h = build_viewer.build_html(pkg)
    # uncertainty panel with per-unit frequencies and the resampling method
    assert "UNCERTAINTY (BOOTSTRAP" in h
    assert ("nondominated" in h.lower()) or ("%" in h)
    assert "independent" in h            # run_study uses the independent-pixel bootstrap
    # frontier panel appears because run_study yields >=2 eligible units
    assert pkg.get("frontier")
    assert ("PARETO FRONTIER" in h) or ("layer" in h.lower())


def test_html_injection_is_escaped():
    pkg = study.run_study()
    evil = "<script>alert(1)</script>"
    # inject into fields the viewer renders (eligibility reason, source label, target body)
    uid = next(iter(pkg["baseline_vectors"]))
    pkg["eligibility"][uid]["reason"] = evil
    pkg["profile"]["source_label"] = evil
    pkg["profile"]["target_body"] = evil
    h = build_viewer.build_html(pkg)
    assert evil not in h                      # raw script tag must not survive
    assert "&lt;script&gt;" in h              # it should appear escaped
