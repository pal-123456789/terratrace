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


def test_html_injection_is_escaped():
    pkg = study.run_study()
    evil = "<script>alert(1)</script>"
    # inject into fields the viewer renders
    uid = next(iter(pkg["baseline_vectors"]))
    pkg["eligibility"][uid]["reason"] = evil
    pkg["profile"]["source_label"] = evil
    h = build_viewer.build_html(pkg)
    assert evil not in h                      # raw script tag must not survive
    assert "&lt;script&gt;" in h              # it should appear escaped
