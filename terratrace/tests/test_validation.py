"""Scientific-correctness validation suite tests.

Drives ``terratrace.validation`` (the real engine on synthetic terrains with
known relationships) and asserts the headline oracle, per-check record shape,
determinism, three individual checks, and that key metrics are scientifically
sane. Dependency-free: plain ``def test_*()``, assert-based, no pytest, no
network. ``run_validation()`` is ~2-3 s, so it is cached and run only twice
total across the whole module.
"""
from terratrace import validation


# Record ``name`` values (the ``check_`` prefix is stripped inside the module).
_EXPECTED_NAMES = (
    "self_distance_zero",
    "translation_invariance",
    "rotation90_invariance",
    "monotonic_roughness_discrimination",
    "dominance_recovery",
    "null_control",
    "water_candidate_blocked",
    "determinism",
    "curvature_zero_on_plane",
    "vrm_discriminates_roughness",
    "roughness_hurst_sane",
    "openness_flat",
    "openness_peak",
    "openness_pit_mirror",
    "geomorphon_flat",
    "geomorphon_cone_peak",
    "geomorphon_bowl_pit",
    "geomorphon_tilt_slope",
    "geomorphon_relief_invariance",
    "significance_clear_winner",
    "significance_near_tie_is_honest",
    "confidence_robust_on_clear_winner",
    "confidence_fragile_or_tie_on_near_tie",
    "spectral_sinusoid_peak",
    "spectral_white_noise_flat",
    "spectral_parseval",
    "anisotropy_ridges_oriented",
    "anisotropy_isotropic_low",
    "multiscale_identical_is_layer1_all_scales",
    "kh_roughness_plane_is_zero_rough_discriminates",
    "iwahashi_pike_texture_and_convexity",
    "drainage_flow_conservation_and_dissection",
    "wavelet_checkerboard_finest",
    "hypsometry_ramp_and_cross_consistency",
    "normal_roughness_plane_zero_discriminates",
    "tpi_peak_ridge_pit_valley",
    "fractal_plane_two_rough_higher",
    "lacunarity_uniform_one_clustered_higher",
    "entropy_constant_zero_complex_higher",
    "slope_area_concave_positive_theta",
    "twi_decreases_with_slope",
    "convergence_cone_divergent_bowl_convergent",
    "svf_flat_is_one_pit_lower",
    "multiscale_tpi_cone_bowl_plane",
    "variogram_whitenoise_vs_plane",
    "roughness_length_ramp_hurst_white_flat",
    "curvature_classes_dome_bowl_saddle_plane",
    "fabric_plane_cluster_vs_rough_isotropic",
    "openness_difference_cone_ridge_bowl_valley",
    "melton_flat_zero_and_cross_check_hi",
    "transect_plane_constant_slope",
)

# New line-of-sight morphology oracles added on top of the original battery.
_MORPH_NAMES = (
    "openness_flat",
    "openness_peak",
    "openness_pit_mirror",
    "geomorphon_flat",
    "geomorphon_cone_peak",
    "geomorphon_bowl_pit",
    "geomorphon_tilt_slope",
    "geomorphon_relief_invariance",
)

# Statistical-layer oracles: resampling significance + decision-confidence verdict.
_SIG_CONF_NAMES = (
    "significance_clear_winner",
    "significance_near_tie_is_honest",
    "confidence_robust_on_clear_winner",
    "confidence_fragile_or_tie_on_near_tie",
)

# Spectral (radially-averaged PSD) + anisotropy (directional fabric) oracles.
_SPECTRAL_ANISO_NAMES = (
    "spectral_sinusoid_peak",
    "spectral_white_noise_flat",
    "spectral_parseval",
    "anisotropy_ridges_oriented",
    "anisotropy_isotropic_low",
)

# Wavelet / hypsometry / normal-roughness / TPI-landform oracles (four new
# single-tile morphology descriptors wired into the validation battery).
_NEW_DESCRIPTOR_NAMES = (
    "wavelet_checkerboard_finest",
    "hypsometry_ramp_and_cross_consistency",
    "normal_roughness_plane_zero_discriminates",
    "tpi_peak_ridge_pit_valley",
)

# Fractal / lacunarity / entropy / slope-area oracles (four more single-tile
# morphology descriptors wired into the validation battery).
_FBC_NAMES = (
    "fractal_plane_two_rough_higher",
    "lacunarity_uniform_one_clustered_higher",
    "entropy_constant_zero_complex_higher",
    "slope_area_concave_positive_theta",
)

_N_CHECKS = len(_EXPECTED_NAMES)

_REPORT_CACHE = []


def _report():
    """One cached ``run_validation()`` report shared across tests."""
    if not _REPORT_CACHE:
        _REPORT_CACHE.append(validation.run_validation())
    return _REPORT_CACHE[0]


def _find(report, name):
    for c in report["checks"]:
        if c["name"] == name:
            return c
    raise AssertionError(f"check {name!r} not in report")


def test_run_validation_headline_oracle():
    """The engine is scientifically correct: all checks pass."""
    report = _report()
    assert report["all_passed"] is True
    assert report["passed"] == _N_CHECKS
    assert report["failed"] == 0
    assert len(report["checks"]) == _N_CHECKS
    assert isinstance(report["package_hash"], str)
    assert report["package_hash"], "package_hash must be a non-empty string"


def test_every_check_record_shape_and_names():
    """Each record has name/passed/detail/metrics, passes, and the names are
    unique and exactly the expected set."""
    report = _report()
    names = []
    for c in report["checks"]:
        for key in ("name", "passed", "detail", "metrics"):
            assert key in c, (key, c)
        assert isinstance(c["name"], str)
        assert isinstance(c["detail"], str)
        assert isinstance(c["metrics"], dict)
        assert isinstance(c["passed"], bool), c["name"]
        assert c["passed"] is True, (c["name"], c["detail"])
        names.append(c["name"])
    assert len(names) == _N_CHECKS
    assert len(set(names)) == _N_CHECKS, f"duplicate check names: {names}"
    assert set(names) == set(_EXPECTED_NAMES), set(names) ^ set(_EXPECTED_NAMES)


def test_run_validation_is_deterministic():
    """Two independent runs agree on package_hash, the ordered (name, passed)
    sequence of every check, and the pass/fail tallies."""
    first = _report()
    second = validation.run_validation()
    assert first["package_hash"] == second["package_hash"]
    assert (first["passed"], first["failed"]) == (second["passed"], second["failed"])
    seq_a = [(c["name"], c["passed"]) for c in first["checks"]]
    seq_b = [(c["name"], c["passed"]) for c in second["checks"]]
    assert seq_a == seq_b
    outcomes_a = {c["name"]: c["passed"] for c in first["checks"]}
    outcomes_b = {c["name"]: c["passed"] for c in second["checks"]}
    assert outcomes_a == outcomes_b


def test_new_morphology_checks_present_and_pass():
    """The eight added openness/geomorphon oracles are registered in the report
    and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _MORPH_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_self_distance_zero_passes():
    rec = validation.check_self_distance_zero()
    assert rec["name"] == "self_distance_zero"
    assert rec["passed"] is True, rec["detail"]


def test_check_dominance_recovery_passes():
    rec = validation.check_dominance_recovery()
    assert rec["name"] == "dominance_recovery"
    assert rec["passed"] is True, rec["detail"]


def test_check_water_candidate_blocked_passes():
    rec = validation.check_water_candidate_blocked()
    assert rec["name"] == "water_candidate_blocked"
    assert rec["passed"] is True, rec["detail"]


def test_check_curvature_zero_on_plane_passes():
    """Every curvature descriptor vanishes on a tilted plane."""
    rec = validation.check_curvature_zero_on_plane()
    assert rec["name"] == "curvature_zero_on_plane"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert max(abs(m["profile"]), abs(m["plan"]), abs(m["mean"])) < 1e-6, m


def test_check_vrm_discriminates_roughness_passes():
    """VRM is ~0 on a plane and strictly increases with roughness amplitude,
    always bounded in [0, 1]."""
    rec = validation.check_vrm_discriminates_roughness()
    assert rec["name"] == "vrm_discriminates_roughness"
    assert rec["passed"] is True, rec["detail"]
    seq = rec["metrics"]["sequence"]
    assert seq[0] <= 1e-9, seq
    assert all(seq[i] < seq[i + 1] for i in range(len(seq) - 1)), seq
    assert all(0.0 <= s <= 1.0 for s in seq), seq


def test_check_roughness_hurst_sane_passes():
    """Hurst exponent ~1 for a smooth ramp, <0.1 for white noise."""
    rec = validation.check_roughness_hurst_sane()
    assert rec["name"] == "roughness_hurst_sane"
    assert rec["passed"] is True, rec["detail"]
    assert abs(rec["metrics"]["hurst_ramp"] - 1.0) < 1e-6, rec["metrics"]
    assert rec["metrics"]["hurst_noise"] < 0.1, rec["metrics"]


def test_monotonic_roughness_metric_strictly_increases():
    """Rougher candidates sit farther on the ruggedness axis — the engine has
    real discriminating power."""
    rec = _find(_report(), "monotonic_roughness_discrimination")
    rug = rec["metrics"]["ruggedness"]
    assert isinstance(rug, list) and len(rug) >= 2, rug
    assert all(rug[i] < rug[i + 1] for i in range(len(rug) - 1)), rug


def test_dominance_recovery_metric_rank_and_detail():
    """Closer candidate is Pareto layer 1 (and recommended); farther one is
    layer >= 2."""
    rec = _find(_report(), "dominance_recovery")
    rank = rec["metrics"]["rank"]
    assert rank["near"] == 1, rank
    assert rank["far"] >= 2, rank
    assert "recommended=near" in rec["detail"], rec["detail"]


def test_check_openness_flat_passes():
    """Flat plane: positive and negative openness are 90 deg everywhere."""
    rec = validation.check_openness_flat()
    assert rec["name"] == "openness_flat"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["positive_dev"] < 1e-6 and m["negative_dev"] < 1e-6, m


def test_check_openness_peak_passes():
    """Cone apex: positive openness > 90 and negative openness < 90."""
    rec = validation.check_openness_peak()
    assert rec["name"] == "openness_peak"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["positive"] > 90.0 > rec["metrics"]["negative"], rec["metrics"]


def test_check_openness_pit_mirror_passes():
    """Bowl centre mirrors a peak: negative openness > 90 and positive < 90."""
    rec = validation.check_openness_pit_mirror()
    assert rec["name"] == "openness_pit_mirror"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["negative"] > 90.0 > rec["metrics"]["positive"], rec["metrics"]


def test_check_geomorphon_flat_passes():
    """Flat plane is classified 'flat' almost everywhere."""
    rec = validation.check_geomorphon_flat()
    assert rec["name"] == "geomorphon_flat"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["flat_fraction"] > 0.95, rec["metrics"]
    assert rec["metrics"]["dominant"] == "flat", rec["metrics"]


def test_check_geomorphon_cone_peak_passes():
    """Cone apex classifies as 'peak' (FORM_NAMES index 1)."""
    rec = validation.check_geomorphon_cone_peak()
    assert rec["name"] == "geomorphon_cone_peak"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["form"] == "peak", rec["metrics"]
    assert rec["metrics"]["code"] == 1, rec["metrics"]


def test_check_geomorphon_bowl_pit_passes():
    """Bowl centre classifies as 'pit' (the antisymmetric mirror of the apex)."""
    rec = validation.check_geomorphon_bowl_pit()
    assert rec["name"] == "geomorphon_bowl_pit"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["form"] == "pit", rec["metrics"]


def test_check_geomorphon_tilt_slope_passes():
    """A uniform planar tilt is dominated by 'slope'."""
    rec = validation.check_geomorphon_tilt_slope()
    assert rec["name"] == "geomorphon_tilt_slope"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["dominant"] == "slope", rec["metrics"]


def test_check_geomorphon_relief_invariance_passes():
    """Landform composition is exactly invariant to a +100 m vertical offset."""
    rec = validation.check_geomorphon_relief_invariance()
    assert rec["name"] == "geomorphon_relief_invariance"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["forms"] >= 1, rec["metrics"]


def test_new_significance_confidence_checks_present_and_pass():
    """The four significance / decision-confidence oracles are registered in the
    report and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _SIG_CONF_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_significance_clear_winner_passes():
    """A clear single winner's recommendation is permutation-significant and the
    recommended unit is the closer candidate ('near')."""
    rec = validation.check_significance_clear_winner()
    assert rec["name"] == "significance_clear_winner"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["recommended"] == "near", rec["metrics"]
    assert rec["metrics"]["recommendation_significant"] is True, rec["metrics"]


def test_check_significance_near_tie_is_honest_passes():
    """A near-tie is reported honestly: not a lone recommendation, or the
    recommendation is NOT significant (no manufactured significance)."""
    rec = validation.check_significance_near_tie_is_honest()
    assert rec["name"] == "significance_near_tie_is_honest"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["state"] != "RECOMMEND_FOLLOW_UP" or m["recommendation_significant"] is False, m


def test_check_confidence_robust_on_clear_winner_passes():
    """Clear winner -> 'robust' verdict with bootstrap + significance both
    evaluated and positive (a documented rule over per-signal classes, no score)."""
    rec = validation.check_confidence_robust_on_clear_winner()
    assert rec["name"] == "confidence_robust_on_clear_winner"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["verdict"] == "robust", rec["metrics"]
    assert rec["metrics"]["significant"] is True, rec["metrics"]


def test_check_confidence_fragile_or_tie_on_near_tie_passes():
    """Near-tie -> the decision confidence is NEVER 'robust' (fragile/qualified/
    tie/indeterminate only)."""
    rec = validation.check_confidence_fragile_or_tie_on_near_tie()
    assert rec["name"] == "confidence_fragile_or_tie_on_near_tie"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["verdict"] != "robust", rec["metrics"]
    assert rec["metrics"]["verdict"] in {"fragile", "qualified", "tie",
                                         "indeterminate"}, rec["metrics"]


def test_new_spectral_anisotropy_checks_present_and_pass():
    """The five added spectral + anisotropy oracles are registered in the report
    and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _SPECTRAL_ANISO_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_spectral_sinusoid_peak_passes():
    """A period-8 sinusoid peaks at ~8 m (within one radial bin: band 6..11)."""
    rec = validation.check_spectral_sinusoid_peak()
    assert rec["name"] == "spectral_sinusoid_peak"
    assert rec["passed"] is True, rec["detail"]
    assert 6.0 <= rec["metrics"]["peak_wavelength_m"] <= 11.0, rec["metrics"]


def test_check_spectral_white_noise_flat_passes():
    """White noise has a ~flat spectrum: abs(spectral_slope) < 1.0."""
    rec = validation.check_spectral_white_noise_flat()
    assert rec["name"] == "spectral_white_noise_flat"
    assert rec["passed"] is True, rec["detail"]
    assert abs(rec["metrics"]["spectral_slope"]) < 1.0, rec["metrics"]


def test_check_spectral_parseval_passes():
    """Summed spectral power recovers the detrended variance within 25%."""
    rec = validation.check_spectral_parseval()
    assert rec["name"] == "spectral_parseval"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["rel_error"] <= 0.25, rec["metrics"]


def test_check_anisotropy_ridges_oriented_passes():
    """Parallel ridges are strongly anisotropic, strike ~90 deg (due north)."""
    rec = validation.check_anisotropy_ridges_oriented()
    assert rec["name"] == "anisotropy_ridges_oriented"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["strength"] > 0.5, rec["metrics"]
    assert abs(rec["metrics"]["orientation_deg"] - 90.0) <= 25.0, rec["metrics"]


def test_check_anisotropy_isotropic_low_passes():
    """Isotropic noise has no preferred direction: strength < 0.25."""
    rec = validation.check_anisotropy_isotropic_low()
    assert rec["name"] == "anisotropy_isotropic_low"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["strength"] < 0.25, rec["metrics"]


def test_new_multiscale_check_present_and_passes():
    """The scale-resolved analog oracle is registered in the report and passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    name = "multiscale_identical_is_layer1_all_scales"
    assert name in present, f"{name!r} not registered in run_validation()"
    assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_multiscale_identical_is_layer1_all_scales_passes():
    """A near twin is a layer-1 analog at every swept support (fraction 1.0) and
    the far unit is NOT layer 1 at the finest support."""
    rec = validation.check_multiscale_identical_is_layer1_all_scales()
    assert rec["name"] == "multiscale_identical_is_layer1_all_scales"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["near_fraction_layer1"] == 1.0, rec["metrics"]
    assert rec["metrics"]["far_layer_finest"] != 1, rec["metrics"]


def test_new_kh_roughness_check_present_and_passes():
    """The Kreslavsky & Head differential-slope roughness oracle is registered in
    the report and passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    name = "kh_roughness_plane_is_zero_rough_discriminates"
    assert name in present, f"{name!r} not registered in run_validation()"
    assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_kh_roughness_plane_is_zero_rough_discriminates_passes():
    """A tilted plane has ~0 baseline roughness (< 1e-6 deg) and a rough surface
    strictly exceeds it (the metric discriminates roughness)."""
    rec = validation.check_kh_roughness_plane_is_zero_rough_discriminates()
    assert rec["name"] == "kh_roughness_plane_is_zero_rough_discriminates"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["plane_roughness"] < 1e-6, m
    assert m["rough_roughness"] > m["plane_roughness"], m


def test_new_iwahashi_pike_check_present_and_passes():
    """The Iwahashi & Pike (2007) geometric-signature oracle is registered in the
    report and passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    name = "iwahashi_pike_texture_and_convexity"
    assert name in present, f"{name!r} not registered in run_validation()"
    assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_iwahashi_pike_texture_and_convexity_passes():
    """Surface texture discriminates roughness (rough > smooth plane) and local
    convexity separates a dome centre (high) from a basin centre (low)."""
    rec = validation.check_iwahashi_pike_texture_and_convexity()
    assert rec["name"] == "iwahashi_pike_texture_and_convexity"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["texture_rough"] > m["texture_smooth"], m
    assert m["dome_convexity"] > m["basin_convexity"], m


def test_new_drainage_check_present_and_passes():
    """The depression-filled D8 flow-accumulation oracle is registered in the
    report and passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    name = "drainage_flow_conservation_and_dissection"
    assert name in present, f"{name!r} not registered in run_validation()"
    assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_drainage_flow_conservation_and_dissection_passes():
    """Flow conservation holds exactly (sum of outlet acc == n_finite) and the
    drainage texture discriminates roughness (rough concentrates flow more and
    routes less organised accumulation than a smooth plane)."""
    rec = validation.check_drainage_flow_conservation_and_dissection()
    assert rec["name"] == "drainage_flow_conservation_and_dissection"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert abs(m["outlet_sum"] - m["n_finite"]) < 1e-6, m
    assert m["rough_max_acc_fraction"] > m["smooth_max_acc_fraction"], m
    assert m["rough_mean_log_acc"] < m["smooth_mean_log_acc"], m


def test_new_descriptor_oracles_present_and_pass():
    """The four added wavelet / hypsometry / normal-roughness / TPI-landform
    oracles are registered in the report and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _NEW_DESCRIPTOR_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_wavelet_checkerboard_finest_passes():
    """A period-2 checkerboard puts all Haar detail energy at the finest level."""
    rec = validation.check_wavelet_checkerboard_finest()
    assert rec["name"] == "wavelet_checkerboard_finest"
    assert rec["passed"] is True, rec["detail"]
    assert rec["metrics"]["dominant_level"] == 1, rec["metrics"]


def test_check_hypsometry_ramp_and_cross_consistency_passes():
    """A symmetric ramp has hypsometric integral ~0.5 and the two independent
    implementations agree to within 1e-6."""
    rec = validation.check_hypsometry_ramp_and_cross_consistency()
    assert rec["name"] == "hypsometry_ramp_and_cross_consistency"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert abs(m["integral"] - 0.5) < 0.02, m
    assert m["abs_diff"] < 1e-6, m


def test_check_normal_roughness_plane_zero_discriminates_passes():
    """Surface-normal roughness is ~0 on a tilted plane and strictly greater on a
    seeded rough surface."""
    rec = validation.check_normal_roughness_plane_zero_discriminates()
    assert rec["name"] == "normal_roughness_plane_zero_discriminates"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["plane_roughness"] < 1e-6, m
    assert m["rough_roughness"] > m["plane_roughness"], m


def test_check_tpi_peak_ridge_pit_valley_passes():
    """A radial cone apex classifies as 'ridge' and a radial bowl centre as
    'valley' (the two Weiss TPI slope-position extremes)."""
    rec = validation.check_tpi_peak_ridge_pit_valley()
    assert rec["name"] == "tpi_peak_ridge_pit_valley"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["apex_form"] == "ridge", m
    assert m["pit_form"] == "valley", m


def test_new_fbc_descriptor_oracles_present_and_pass():
    """The four added fractal / lacunarity / entropy / slope-area oracles are
    registered in the report and every one passes."""
    report = _report()
    present = {c["name"] for c in report["checks"]}
    for name in _FBC_NAMES:
        assert name in present, f"{name!r} not registered in run_validation()"
        assert _find(report, name)["passed"] is True, _find(report, name)["detail"]


def test_check_fractal_plane_two_rough_higher_passes():
    """A tilted plane's box-counting dimension is ~2 and a seeded rough field
    exceeds a smooth sinusoid's dimension."""
    rec = validation.check_fractal_plane_two_rough_higher()
    assert rec["name"] == "fractal_plane_two_rough_higher"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert abs(m["plane_dimension"] - 2.0) < 0.25, m
    assert m["rough_dimension"] > m["sinusoid_dimension"], m


def test_check_lacunarity_uniform_one_clustered_higher_passes():
    """A uniform field has lacunarity exactly 1.0 and a sparse clustered field is
    gappier than a smooth gradient."""
    rec = validation.check_lacunarity_uniform_one_clustered_higher()
    assert rec["name"] == "lacunarity_uniform_one_clustered_higher"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert abs(m["uniform"] - 1.0) < 1e-9, m
    assert m["clustered"] > m["gradient"], m


def test_check_entropy_constant_zero_complex_higher_passes():
    """A constant field has zero slope entropy and a complex multi-scale surface
    exceeds a single ramp (also zero)."""
    rec = validation.check_entropy_constant_zero_complex_higher()
    assert rec["name"] == "entropy_constant_zero_complex_higher"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["constant"] == 0.0, m
    assert m["complex"] > m["ramp"], m


def test_check_slope_area_concave_positive_theta_passes():
    """A concave z = c*(D - x)^2 surface has a positive Flint concavity index
    with a credible log-log fit."""
    rec = validation.check_slope_area_concave_positive_theta()
    assert rec["name"] == "slope_area_concave_positive_theta"
    assert rec["passed"] is True, rec["detail"]
    m = rec["metrics"]
    assert m["flint_theta"] > 0.0, m
    assert m["r2"] > 0.3, m
