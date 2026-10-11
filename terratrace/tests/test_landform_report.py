"""Landform-rendering fixtures for report_html + build_viewer (dependency-free).

A study package MAY optionally carry 'landform', 'landform_previews' and
'openness_previews' keys (present only when a study was run with landform=True).
These tests assert both renderers surface that block when present and stay
byte-for-byte unchanged when it is absent. Plain asserts, top-level test_*,
offline, no third-party deps (mirrors tests/test_study.py).
"""
from terratrace import study, report_html, build_viewer

# The exact tiny 1x1 PNG data-URI placeholder the task specifies.
PNG = "data:image/png;base64,iVBORw0KGgo="
FORMS = ("flat", "peak", "ridge", "shoulder", "spur", "slope",
         "hollow", "footslope", "valley", "pit")


def _composition(dominant):
    """A 10-form geomorphon composition summing to 1.0, peaked on `dominant`."""
    frac = {f: 0.05 for f in FORMS}      # ten forms x 0.05 = 0.50
    frac[dominant] = 0.55                # +0.50 over its old 0.05 -> grand total 1.0
    return frac


def _landform_block():
    def rec(dom):
        return {
            "composition": _composition(dom),
            "dominant_form": dom,
            "openness": {"positive_median": 1.52, "negative_median": 1.48,
                         "positive_p10": 1.40, "positive_p90": 1.65,
                         "negative_p10": 1.35, "negative_p90": 1.60},
            "spectrum": [[float((i + j) % 7) for j in range(9)] for i in range(9)],
        }
    return {"u_alpha": rec("slope"), "u_beta": rec("flat")}


def _pkg_with_landform(previews=True):
    """A real, valid study package (so both renderers get their scaffolding) with a
    hand-constructed landform block attached."""
    pkg = study.run_study()
    pkg["landform"] = _landform_block()
    if previews:
        pkg["landform_previews"] = {"u_alpha": PNG, "u_beta": PNG}
        pkg["openness_previews"] = {"u_alpha": PNG, "u_beta": PNG}
    return pkg


def test_report_renders_landform_section_tables_and_dominant():
    h = report_html.study_report_html(_pkg_with_landform(previews=False))
    assert "Landform structure (geomorphons + openness)" in h
    assert "Landform" in h
    # form-name column headers (a canonical form + the compound 'footslope')
    assert "slope" in h and "footslope" in h
    # both landform units and their dominant forms are rendered
    assert "u_alpha" in h and "u_beta" in h
    # composition rendered as a percentage (0.55 dominant -> 55.0%)
    assert "55.0%" in h
    # positive/negative openness medians
    assert "1.52" in h and "1.48" in h
    # honest caption + the two literature references
    assert "Jasiewicz" in h and "Yokoyama" in h
    assert "Morphology only" in h and "not traversability" in h


def test_report_embeds_landform_and_openness_preview_images():
    h = report_html.study_report_html(_pkg_with_landform(previews=True))
    assert "<img" in h
    assert PNG in h
    assert "categorical landform map" in h
    assert "positive-openness" in h
    # still a complete, self-contained document (no external assets)
    assert h.lstrip().lower().startswith("<!doctype html")
    for needle in ("http://", "https://", "//cdn", "<link", "<script", "url("):
        assert needle not in h, needle


def test_report_backward_compatible_without_landform():
    plain = report_html.study_report_html(study.run_study())
    assert "Landform structure" not in plain
    assert "<h2>Landform structure (geomorphons + openness)</h2>" not in plain
    # empty / None landform collapses to no section AND is byte-identical to a package
    # that never carried the key (proves the guard adds no stray output / newline).
    for empty in ({}, None):
        pkg = study.run_study()
        pkg["landform"] = empty
        assert report_html.study_report_html(pkg) == plain


def test_viewer_renders_landform_panel():
    h = build_viewer.build_html(_pkg_with_landform(previews=False))
    assert "LANDFORM STRUCTURE (GEOMORPHONS + OPENNESS)" in h
    assert "slope" in h and "footslope" in h
    assert "u_alpha" in h and "u_beta" in h
    assert "55.0%" in h
    assert "1.52" in h and "1.48" in h
    assert "Jasiewicz" in h and "Yokoyama" in h
    assert "Morphology only" in h


def test_viewer_embeds_preview_images():
    h = build_viewer.build_html(_pkg_with_landform(previews=True))
    assert "<img" in h and PNG in h
    assert "categorical landform map" in h and "positive-openness map" in h


def test_viewer_backward_compatible_without_landform():
    assert build_viewer._landform_section(study.run_study()) == ""
    plain = build_viewer.build_html(study.run_study())
    assert "LANDFORM STRUCTURE" not in plain
    # empty / None landform -> still no panel (no leak, no crash)
    for empty in ({}, None):
        pkg = study.run_study()
        pkg["landform"] = empty
        assert build_viewer._landform_section(pkg) == ""


def test_landform_rendering_is_deterministic():
    pkg = _pkg_with_landform(previews=True)
    assert report_html.study_report_html(pkg) == report_html.study_report_html(pkg)
    assert build_viewer.build_html(pkg) == build_viewer.build_html(pkg)
