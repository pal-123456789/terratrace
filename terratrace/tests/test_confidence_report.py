"""Decision-confidence + permutation-significance rendering for both the HTML
report (``report_html.study_report_html``) and the offline viewer
(``build_viewer.build_html``). Dependency-free, assert-based; run via
``tests/run_tests.py`` or by calling the ``test_*`` functions directly.

A study package MAY carry an opt-in ``significance`` block and/or a ``bootstrap``
block. When EITHER is present both renderers surface a "Decision confidence"
section: the non-composite categorical verdict, its three independent robustness
signals (bootstrap non-domination, permutation significance vs the runner-up,
lens/support stability), the caveats (what was NOT evaluated), and -- for an
evaluated significance block -- a per-metric permutation table vs the runner-up.
When NEITHER is present (the default ``run_study()``) NO such section appears and
the output is byte-for-byte unchanged.

Backward-compat is proved WITHOUT pinning any absolute ``package_hash`` literal
(that value is NumPy-build dependent): the proof is key-absence + the gated
rendering helpers returning '' for the default package, and every rendered value
is read from the live package so it stays in lock-step regardless of NumPy build.
These are DISTRIBUTION-SHAPE resampling statistics only -- not a physical,
geological, or mission claim.
"""
from terratrace import study, synthetic, report_html, build_viewer


def _geomorphic_scene():
    """A 3-unit scene (mirrors tests/test_study.py's geomorphic fixture): 'near'
    sits close to the reference and 'far' sits far from it -> a clear, significant
    RECOMMEND_FOLLOW_UP with 'far' as the runner-up."""
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    return {
        "ref": base + synthetic.rough_field((64, 64), 0.8, seed=1),
        "near": base + synthetic.rough_field((64, 64), 0.9, seed=2),
        "far": base + synthetic.rough_field((64, 64), 4.0, seed=3),
    }


def _rich_pkg():
    """A rich package: significance (permutation) + bootstrap both computed."""
    raw = _geomorphic_scene()
    rights = {k: "verified_allowed" for k in raw}
    return study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                               target_support_m=10.0, significance=True,
                               n_perm=200, n_boot=80)


def test_rich_package_renders_confidence_in_report_and_viewer():
    from terratrace import confidence
    pkg = _rich_pkg()
    assert pkg["result_state"] == "RECOMMEND_FOLLOW_UP"
    # the exact gate the renderers use
    assert bool(pkg.get("significance")) or bool(pkg.get("bootstrap"))
    conf = confidence.decision_confidence(pkg)
    verdict = conf["verdict"].upper()                       # e.g. "ROBUST"
    sig = pkg["significance"]
    runner = sig["runner_up"]                               # "far"
    # a per-metric permutation p-value, formatted exactly as both renderers do
    pstr = f"{sig['per_metric']['slope']['p_value_one_sided']:.4g}"
    rep = report_html.study_report_html(pkg)
    view = build_viewer.build_html(pkg)
    for h in (rep, view):
        assert "confidence" in h                            # honest caption text
        assert verdict in h                                 # prominent uppercase verdict
        assert pstr in h                                    # a metric p-value
        assert runner in h                                  # the runner-up name
    # report-specific markers
    assert "<h2>Decision confidence</h2>" in rep
    assert "Significance vs runner-up" in rep
    # viewer-specific markers
    assert "DECISION CONFIDENCE" in view
    assert "Significance vs runner-up" in view
    # the honest "no composite score" firewall rides along in both
    assert "no composite score" in rep and "no composite score" in view


def test_significance_table_lists_every_metric_and_overall_flag():
    pkg = _rich_pkg()
    rep = report_html.study_report_html(pkg)
    view = build_viewer.build_html(pkg)
    # all four per-metric rows surface, including the scalar connectivity axis
    for m in ("slope", "relief", "ruggedness", "connectivity"):
        assert m in rep and m in view, m
    # the permutation metrics vs the scalar axis are both labelled honestly
    assert "permutation" in rep and "permutation" in view
    assert "scalar" in rep and "scalar" in view
    # the recommended unit is named alongside the runner-up
    assert pkg["significance"]["recommended_unit"] in rep
    assert pkg["significance"]["recommended_unit"] in view


def test_evaluated_false_significance_renders_honest_line_not_table():
    # All candidates blocked (rights unverified) -> BLOCKED, significance attached as
    # evaluated=False. significance is truthy so the confidence section still shows,
    # but the significance block renders ONE honest line (its reason), no table.
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    raw = {"ref": base,
           "c1": base + synthetic.rough_field((64, 64), 0.9, seed=2),
           "c2": base + synthetic.rough_field((64, 64), 1.0, seed=3)}
    rights = {"ref": "verified_allowed", "c1": "unknown", "c2": "pending"}
    pkg = study.compare_units(raw, rights, native_posting_m=10.0, reference_id="ref",
                              target_support_m=10.0, significance=True, n_perm=50)
    assert pkg["result_state"] != "RECOMMEND_FOLLOW_UP"
    assert pkg["significance"]["evaluated"] is False
    rep_tab = report_html._significance_table_html(pkg)
    view_tab = build_viewer._significance_section_viewer(pkg)
    for frag in (rep_tab, view_tab):
        assert "not evaluated" in frag
        assert "<table" not in frag                         # no per-metric table
    # the section still renders (gated on significance being present/truthy)
    assert "Decision confidence" in report_html.study_report_html(pkg)
    assert "DECISION CONFIDENCE" in build_viewer.build_html(pkg)


def test_bootstrap_only_shows_confidence_without_significance_table():
    # bootstrap present but significance absent -> the confidence section appears
    # (gate satisfied via bootstrap) but carries NO per-metric significance table.
    pkg = study.run_study(n_boot=40)
    assert pkg.get("bootstrap") and not pkg.get("significance")
    rep = report_html.study_report_html(pkg)
    view = build_viewer.build_html(pkg)
    assert "Decision confidence" in rep and "DECISION CONFIDENCE" in view
    # no significance sub-table was built (nothing was permutation-tested)
    assert report_html._significance_table_html(pkg) == ""
    assert build_viewer._significance_section_viewer(pkg) == ""
    assert "Significance vs runner-up" not in rep


def test_default_study_has_no_confidence_section_byte_identity_guard():
    # The default run_study() carries NEITHER block, so the gated helpers add
    # nothing: this is the byte-identity guard (an empty helper return is appended
    # under an `if` in the report, and sits adjacent to {landform_section} in the
    # viewer template, so it contributes zero bytes).
    pkg = study.run_study()
    assert not pkg.get("significance") and not pkg.get("bootstrap")
    assert report_html._confidence_html(pkg) == ""
    assert build_viewer._confidence_section(pkg) == ""
    assert report_html._significance_table_html(pkg) == ""
    assert build_viewer._significance_section_viewer(pkg) == ""
    rep = report_html.study_report_html(pkg)
    view = build_viewer.build_html(pkg)
    assert "Decision confidence" not in rep
    assert "DECISION CONFIDENCE" not in view


def test_confidence_rendering_is_deterministic():
    pkg = _rich_pkg()
    assert report_html.study_report_html(pkg) == report_html.study_report_html(pkg)
    assert build_viewer.build_html(pkg) == build_viewer.build_html(pkg)
    # and both documents stay fully self-contained (no external assets introduced)
    for h in (report_html.study_report_html(pkg), build_viewer.build_html(pkg)):
        for needle in ("http://", "https://", "//cdn", "<link ", "url("):
            assert needle not in h, needle
