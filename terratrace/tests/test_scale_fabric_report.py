"""Scale & fabric (spectral roughness + directional anisotropy) rendering.

Dependency-free, assert-based (mirrors tests/test_study.py): top-level ``test_*``
functions, plain ``assert``, no pytest. Covers that the opt-in per-unit
``spectral`` / ``anisotropy`` blocks surface in BOTH the HTML report and the
offline viewer when present, are ABSENT (byte-safe) for a default study, gate on
either key, and render deterministically. No package_hash literal is pinned (that
value is float/NumPy-build dependent); only section presence/absence, a rendered
numeric value, and determinism are asserted.
"""
from terratrace import study, report_html, build_viewer, spectral, anisotropy, synthetic

HEADER = "scale &amp; fabric"          # escaped '&'; matches report + viewer (any case)
CAPTION = "not a traversability, hazard, or geologic claim"


def _scene():
    """A 3-unit scene like test_study.py's geomorphic fixture (ref/near/far)."""
    base = synthetic.plane((64, 64), slope_x=0.02, dx=10.0)
    scene = {
        "ref": base + synthetic.rough_field((64, 64), 0.8, seed=1),
        "near": base + synthetic.rough_field((64, 64), 0.9, seed=2),
        "far": base + synthetic.rough_field((64, 64), 4.0, seed=3),
    }
    return scene, {k: "verified_allowed" for k in scene}


def _spectra_package():
    """Build a study package carrying the opt-in scale & fabric blocks.

    Prefers the real path (``compare_units(..., terrain_spectra=True)``); if this
    tree's study.py does not expose that opt-in yet, fall back to a package built
    without it and attach the spectral/anisotropy blocks computed by the real
    spectral/anisotropy modules, so the RENDERING path is exercised either way.
    """
    scene, rights = _scene()
    kw = dict(native_posting_m=10.0, reference_id="ref", target_support_m=10.0)
    try:
        pkg = study.compare_units(scene, rights, terrain_spectra=True, **kw)
    except TypeError:
        pkg = study.compare_units(scene, rights, **kw)
    if not (pkg.get("spectral") or pkg.get("anisotropy")):
        pkg["spectral"] = {u: spectral.spectral_signature(scene[u], dx=10.0) for u in scene}
        pkg["anisotropy"] = {u: anisotropy.anisotropy_signature(scene[u], dx=10.0) for u in scene}
    return pkg


def _spectral_needle(pkg):
    """A rendered numeric spectral value: ref roughness_rms at 4 sig figs (the
    exact form both renderers emit via _num / _f). Guaranteed finite + positive."""
    return f"{float(pkg['spectral']['ref']['roughness_rms']):.4g}"


def test_report_renders_scale_fabric_when_present():
    pkg = _spectra_package()
    h = report_html.study_report_html(pkg)
    assert HEADER in h.lower(), "report must carry the Scale & fabric header"
    assert _spectral_needle(pkg) in h, "a numeric spectral value must render in the report"
    assert CAPTION in h, "honest morphology-only caption must render"


def test_viewer_renders_scale_fabric_when_present():
    pkg = _spectra_package()
    h = build_viewer.build_html(pkg)
    assert HEADER in h.lower(), "viewer must carry the Scale & fabric panel"
    assert _spectral_needle(pkg) in h, "a numeric spectral value must render in the viewer"
    assert CAPTION in h, "honest morphology-only caption must render"


def test_default_report_has_no_scale_fabric_section():
    d = study.run_study()
    assert HEADER not in report_html.study_report_html(d).lower()
    assert report_html._scale_fabric_html(d) == ""      # helper returns '' when keys absent


def test_default_viewer_has_no_scale_fabric_section():
    d = study.run_study()
    assert HEADER not in build_viewer.build_html(d).lower()
    assert build_viewer._scale_fabric_section(d) == ""   # helper returns '' when keys absent


def test_scale_fabric_gate_is_either_key_and_empty_is_absent():
    # Present with ONLY spectral, ONLY anisotropy, or both -> section renders.
    only_sp = {"spectral": {"u": {"roughness_rms": 1.0, "spectral_slope": -2.0}}}
    only_an = {"anisotropy": {"u": {"strength": 0.5, "orientation_deg": 45.0}}}
    for p in (only_sp, only_an):
        assert HEADER in report_html._scale_fabric_html(p).lower()
        assert HEADER in build_viewer._scale_fabric_section(p).lower()
    # Absent / empty -> byte-safe empty string (no section, no crash).
    for p in ({}, {"spectral": {}, "anisotropy": {}}, {"spectral": None, "anisotropy": None}):
        assert report_html._scale_fabric_html(p) == ""
        assert build_viewer._scale_fabric_section(p) == ""


def test_scale_fabric_rendering_is_deterministic():
    pkg = _spectra_package()
    assert report_html.study_report_html(pkg) == report_html.study_report_html(pkg)
    assert build_viewer.build_html(pkg) == build_viewer.build_html(pkg)
