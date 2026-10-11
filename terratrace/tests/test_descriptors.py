"""Tests for the geomorphometric descriptor bank (dependency-free, assert-based).

Mirrors the plain ``def test_*()`` style of test_features.py: no pytest, no
network, small synthetic fixtures with known answers.
"""
import json

import numpy as np

from terratrace import (descriptors, synthetic, geomorphons, spectral, anisotropy,
                        kh_roughness, iwahashi_pike, drainage, fractal, lacunarity,
                        entropy_terrain, slope_area)

MAP_KEYS = ("slope", "relief", "ruggedness", "profile_curvature",
            "plan_curvature", "mean_curvature", "vector_ruggedness")
SCALAR_KEYS = ("aspect_dispersion", "hypsometric_integral",
               "tpi_dispersion", "hurst_exponent")
SUMMARY_KEYS = {"mean", "std", "p10", "p50", "p90"}


def test_bank_on_plane_curvatures_zero_slope_positive():
    plane = synthetic.plane((40, 40), slope_x=0.3, slope_y=0.15, dx=1.0, dy=1.0)
    bank = descriptors.descriptor_bank(plane)
    for key in ("profile_curvature", "plan_curvature", "mean_curvature"):
        assert abs(bank[key]["mean"]) < 1e-6, (key, bank[key]["mean"])
    assert bank["vector_ruggedness"]["p50"] < 1e-6, bank["vector_ruggedness"]["p50"]
    slope = bank["slope"]
    assert all(np.isfinite(v) for v in slope.values()), slope
    for stat in ("mean", "p10", "p50", "p90"):
        assert slope[stat] > 0.0, (stat, slope[stat])


def test_bank_detects_roughness_vs_plane():
    plane = synthetic.plane((40, 40), slope_x=0.3, slope_y=0.1, dx=1.0, dy=1.0)
    rough = plane + synthetic.rough_field((40, 40), amplitude=1.0, seed=11)
    bp = descriptors.descriptor_bank(plane)
    br = descriptors.descriptor_bank(rough)
    assert br["vector_ruggedness"]["p50"] > bp["vector_ruggedness"]["p50"], (
        br["vector_ruggedness"]["p50"], bp["vector_ruggedness"]["p50"])
    assert br["ruggedness"]["mean"] > bp["ruggedness"]["mean"], (
        br["ruggedness"]["mean"], bp["ruggedness"]["mean"])


def test_bank_keys_types_and_json_serialisable():
    z = (synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((40, 40), amplitude=0.5, seed=1))
    bank = descriptors.descriptor_bank(z)
    expected = (set(MAP_KEYS) | set(SCALAR_KEYS) |
                {"structure_function", "surface_area_ratio",
                 "terrain_ruggedness_index", "landform_fraction",
                 "openness", "geomorphons", "spectral", "anisotropy",
                 "kh_roughness", "iwahashi_pike", "drainage",
                 "wavelet", "hypsometry", "normal_roughness", "tpi_landform",
                 "fractal", "lacunarity", "entropy", "slope_area"})
    assert set(bank) == expected, set(bank) ^ expected
    for key in MAP_KEYS:
        summ = bank[key]
        assert isinstance(summ, dict), key
        assert set(summ) == SUMMARY_KEYS, (key, set(summ))
        for v in summ.values():
            assert type(v) is float, (key, v, type(v))
    for key in SCALAR_KEYS:
        assert type(bank[key]) is float, (key, type(bank[key]))
    sf = bank["structure_function"]
    assert isinstance(sf, dict) and sf, "structure_function should be non-empty"
    for k, v in sf.items():
        assert type(k) is str, (k, type(k))
        assert type(v) is float, (k, v, type(v))
    dumped = json.dumps(bank)
    assert isinstance(dumped, str) and len(dumped) > 0
    assert json.loads(dumped)  # round-trips cleanly


def test_bank_is_deterministic():
    z = (synthetic.plane((40, 40), slope_x=0.25, slope_y=0.05)
         + synthetic.rough_field((40, 40), amplitude=0.7, seed=4))
    assert descriptors.descriptor_bank(z) == descriptors.descriptor_bank(z)


def test_summarize_map_all_nan_and_known_median():
    s = descriptors.summarize_map(np.full((5, 5), np.nan))
    assert set(s) == SUMMARY_KEYS
    assert all(np.isnan(v) for v in s.values()), s
    assert all(type(v) is float for v in s.values())

    k = descriptors.summarize_map(np.array([10.0, 20.0, 30.0]))
    assert abs(k["p50"] - 20.0) < 1e-12, k["p50"]
    assert abs(k["mean"] - 20.0) < 1e-12, k["mean"]

    # nan-aware: only finite values contribute to the median.
    km = descriptors.summarize_map(np.array([10.0, 20.0, 30.0, np.nan]))
    assert abs(km["p50"] - 20.0) < 1e-12, km["p50"]
    assert np.isfinite(km["mean"])


def test_bank_vector_matches_bank_headline_scalars():
    z = (synthetic.plane((40, 40), slope_x=0.3, slope_y=0.1)
         + synthetic.rough_field((40, 40), amplitude=0.8, seed=2))
    bank = descriptors.descriptor_bank(z)
    vec = descriptors.bank_vector(z)
    assert len(vec) == len(descriptors.BANK_VECTOR_FIELDS) == 17, len(vec)
    assert all(type(x) is float for x in vec)
    comp = bank["geomorphons"]["composition"]
    expected = (
        bank["slope"]["p50"],
        bank["ruggedness"]["p50"],
        bank["mean_curvature"]["std"],
        bank["vector_ruggedness"]["p50"],
        bank["aspect_dispersion"],
        bank["hypsometric_integral"],
        bank["hurst_exponent"],
        bank["openness"]["positive_median"],
        bank["openness"]["negative_median"],
        comp["peak"],
        comp["ridge"],
        comp["slope"],
        comp["valley"],
        comp["pit"],
        bank["spectral"]["spectral_slope"],
        bank["spectral"]["roughness_rms"],
        bank["anisotropy"]["strength"],
    )
    assert vec == expected, (vec, expected)
    # the first seven positions are frozen (headline morphology scalars)
    assert vec[:7] == (
        bank["slope"]["p50"], bank["ruggedness"]["p50"],
        bank["mean_curvature"]["std"], bank["vector_ruggedness"]["p50"],
        bank["aspect_dispersion"], bank["hypsometric_integral"],
        bank["hurst_exponent"],
    )


# --- added analysis-layer descriptors wired into the bank --------------------

def test_bank_has_added_descriptors_rough_gt_plane_sar_and_serialises():
    plane = synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1, dx=1.0, dy=1.0)
    rough = plane + synthetic.rough_field((40, 40), amplitude=1.0, seed=13)
    bp = descriptors.descriptor_bank(plane)
    br = descriptors.descriptor_bank(rough)

    for key in ("surface_area_ratio", "terrain_ruggedness_index", "landform_fraction"):
        assert key in bp, key
    # the two added map summaries are {mean,std,p10,p50,p90} dicts of plain floats
    for key in ("surface_area_ratio", "terrain_ruggedness_index"):
        assert set(bp[key]) == SUMMARY_KEYS, (key, set(bp[key]))
        assert all(type(v) is float for v in bp[key].values()), key
    # landform_fraction is a dict of plain floats summing to ~1 (or degenerate 0)
    lf = bp["landform_fraction"]
    assert set(lf) == {"ridge", "valley", "flat"}, set(lf)
    assert all(type(v) is float for v in lf.values()), lf

    # a rough field exposes more 3-D surface area per unit plan area than a plane
    assert br["surface_area_ratio"]["mean"] > bp["surface_area_ratio"]["mean"], (
        br["surface_area_ratio"]["mean"], bp["surface_area_ratio"]["mean"])
    assert br["terrain_ruggedness_index"]["mean"] > bp["terrain_ruggedness_index"]["mean"]

    # the whole extended bank still json.dumps and round-trips
    dumped = json.dumps(br)
    assert isinstance(dumped, str) and json.loads(dumped)


# --- openness + geomorphon landform blocks wired into the bank ---------------

def test_bank_has_openness_and_geomorphons_blocks_and_json():
    z = (synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((40, 40), amplitude=1.0, seed=17))
    bank = descriptors.descriptor_bank(z)
    assert "openness" in bank and "geomorphons" in bank

    op = bank["openness"]
    assert set(op) == {"positive_median", "negative_median",
                       "positive_p10", "positive_p90",
                       "negative_p10", "negative_p90"}, set(op)
    assert all(type(v) is float for v in op.values()), op

    gm = bank["geomorphons"]
    assert set(gm) == {"composition", "spectrum", "dominant_form"}, set(gm)
    comp = gm["composition"]
    assert set(comp) == set(geomorphons.FORM_NAMES), set(comp)
    assert all(type(v) is float for v in comp.values()), comp
    assert abs(sum(comp.values()) - 1.0) < 1e-9, sum(comp.values())
    assert gm["dominant_form"] in geomorphons.FORM_NAMES
    spec = gm["spectrum"]
    assert isinstance(spec, list) and len(spec) == 9
    assert all(isinstance(r, list) and len(r) == 9 for r in spec)
    assert all(type(v) is float for r in spec for v in r)

    # the whole extended bank still serialises, round-trips and is deterministic
    assert json.loads(json.dumps(bank))
    assert descriptors.descriptor_bank(z) == bank


def test_bank_openness_flat_is_ninety_and_tilt_dominant_form_is_slope():
    # Yokoyama (2002): a perfectly flat surface has both openness == 90 degrees.
    flat = synthetic.plane((40, 40), slope_x=0.0, slope_y=0.0)
    op = descriptors.descriptor_bank(flat)["openness"]
    assert abs(op["positive_median"] - 90.0) < 1e-6, op["positive_median"]
    assert abs(op["negative_median"] - 90.0) < 1e-6, op["negative_median"]
    # a uniform planar tilt is, geomorphologically, a "slope".
    tilt = synthetic.plane((40, 40), slope_x=0.2, slope_y=0.0)
    gm = descriptors.descriptor_bank(tilt)["geomorphons"]
    assert gm["dominant_form"] == "slope", gm["dominant_form"]


def test_bank_openness_discriminates_peak_from_pit():
    # Positive openness is HIGH on a convex apex; negative openness is HIGH in a
    # concave bowl. Compare the two map-scale summaries additively (analysis
    # layer only -- no decision claim).
    n, c = 41, 20
    i, j = np.indices((n, n))
    cone = -np.hypot(i - c, j - c).astype(float)   # convex apex at centre
    bowl = np.hypot(i - c, j - c).astype(float)     # concave low at centre
    op_cone = descriptors.descriptor_bank(cone)["openness"]
    op_bowl = descriptors.descriptor_bank(bowl)["openness"]
    assert op_cone["positive_median"] > op_bowl["positive_median"], (op_cone, op_bowl)
    assert op_bowl["negative_median"] > op_cone["negative_median"], (op_cone, op_bowl)


# --- scale/fabric (spectral + anisotropy) blocks wired into the bank ---------

SPECTRAL_KEYS = {"spectral_slope", "total_power", "roughness_rms",
                 "peak_wavelength_m", "rough_long", "rough_mid", "rough_short"}
ANISOTROPY_KEYS = {"strength", "orientation_deg", "isotropy", "mean_roughness"}


def test_bank_has_spectral_and_anisotropy_blocks_and_json():
    z = (synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((40, 40), amplitude=1.0, seed=23))
    bank = descriptors.descriptor_bank(z)
    assert "spectral" in bank and "anisotropy" in bank

    sp = bank["spectral"]
    assert set(sp) == SPECTRAL_KEYS, set(sp)
    assert all(type(v) is float for v in sp.values()), sp

    an = bank["anisotropy"]
    assert set(an) == ANISOTROPY_KEYS, set(an)
    assert all(type(v) is float for v in an.values()), an

    # the bank's blocks are exactly the source module signatures (bank dx=1.0)
    assert sp == spectral.spectral_signature(z, dx=1.0)
    assert an == anisotropy.anisotropy_signature(z, dx=1.0)

    # the whole extended bank still serialises, round-trips and is deterministic
    assert json.loads(json.dumps(bank))
    assert descriptors.descriptor_bank(z) == bank


def test_bank_spectral_roughness_and_power_rough_gt_plane():
    plane = synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1)
    rough = plane + synthetic.rough_field((40, 40), amplitude=1.5, seed=29)
    bp = descriptors.descriptor_bank(plane)["spectral"]
    br = descriptors.descriptor_bank(rough)["spectral"]
    # a rough field has larger detrended RMS roughness than a (de-trended) plane
    assert br["roughness_rms"] > bp["roughness_rms"], (br["roughness_rms"], bp["roughness_rms"])
    # total spectral power ~ detrended variance -> also larger for the rough field
    assert br["total_power"] > bp["total_power"], (br["total_power"], bp["total_power"])


def test_bank_anisotropy_strength_lineated_gt_isotropic():
    # Parallel ridges that vary only with the column index j: constant ALONG
    # rows (azimuth 90 deg) -> near-zero directional roughness there, maximal
    # across them -> a strongly lineated fabric. Isotropic noise has no
    # preferred direction, so its fabric strength is far lower.
    n = 48
    _, j = np.indices((n, n))
    lineated = np.sin(2.0 * np.pi * j / 6.0).astype(float)
    isotropic = synthetic.rough_field((n, n), amplitude=1.0, seed=31)
    s_lin = descriptors.descriptor_bank(lineated)["anisotropy"]["strength"]
    s_iso = descriptors.descriptor_bank(isotropic)["anisotropy"]["strength"]
    assert np.isfinite(s_lin) and np.isfinite(s_iso), (s_lin, s_iso)
    assert s_lin > s_iso, (s_lin, s_iso)


def test_bank_vector_tail_is_scale_fabric_scalars_and_prefix_frozen():
    z = (synthetic.plane((40, 40), slope_x=0.25, slope_y=0.05)
         + synthetic.rough_field((40, 40), amplitude=0.9, seed=33))
    bank = descriptors.descriptor_bank(z)
    vec = descriptors.bank_vector(z)
    # the three appended tail fields are the documented scale/fabric scalars
    assert descriptors.BANK_VECTOR_FIELDS[-3:] == (
        "spectral.spectral_slope", "spectral.roughness_rms", "anisotropy.strength")
    assert vec[-3:] == (
        bank["spectral"]["spectral_slope"],
        bank["spectral"]["roughness_rms"],
        bank["anisotropy"]["strength"],
    )
    # the frozen first-seven headline positions are untouched by the append
    assert vec[:7] == (
        bank["slope"]["p50"], bank["ruggedness"]["p50"],
        bank["mean_curvature"]["std"], bank["vector_ruggedness"]["p50"],
        bank["aspect_dispersion"], bank["hypsometric_integral"],
        bank["hurst_exponent"],
    )


# --- Kreslavsky & Head differential-slope roughness block wired into the bank -

KH_ROUGHNESS_KEYS = {"baseline_roughness_fine", "baseline_roughness_coarse",
                     "profile", "profile_loglog_slope"}


def test_bank_has_kh_roughness_block_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((48, 48), amplitude=1.0, seed=37))
    bank = descriptors.descriptor_bank(z)
    assert "kh_roughness" in bank

    kh = bank["kh_roughness"]
    assert set(kh) == KH_ROUGHNESS_KEYS, set(kh)
    for key in ("baseline_roughness_fine", "baseline_roughness_coarse",
                "profile_loglog_slope"):
        assert type(kh[key]) is float, (key, type(kh[key]))
    prof = kh["profile"]
    assert isinstance(prof, dict) and prof
    assert all(type(k) is float for k in prof), prof
    assert all(type(v) is float for v in prof.values()), prof

    # the bank's block is exactly the source-module signature (bank dx=1.0)
    assert kh == kh_roughness.kh_roughness_signature(z, dx=1.0)

    # the whole extended bank still serialises, round-trips and is deterministic
    assert json.loads(json.dumps(bank))
    assert descriptors.descriptor_bank(z) == bank


def test_bank_kh_roughness_plane_zero_and_rough_gt_plane():
    # a tilted plane bends nowhere -> ~0 baseline roughness at every baseline;
    # adding seeded roughness strictly raises it (analysis layer only, no claim).
    plane = synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1)
    rough = plane + synthetic.rough_field((48, 48), amplitude=1.5, seed=41)
    kp = descriptors.descriptor_bank(plane)["kh_roughness"]
    kr = descriptors.descriptor_bank(rough)["kh_roughness"]
    assert kp["baseline_roughness_fine"] < 1e-9, kp["baseline_roughness_fine"]
    assert kp["baseline_roughness_coarse"] < 1e-9, kp["baseline_roughness_coarse"]
    assert kr["baseline_roughness_fine"] > kp["baseline_roughness_fine"], (kr, kp)
    assert kr["baseline_roughness_coarse"] > kp["baseline_roughness_coarse"], (kr, kp)


# --- Iwahashi & Pike (2007) geometric-signature block wired into the bank -----

IWAHASHI_PIKE_KEYS = {"slope_mean", "convexity_mean", "texture_mean",
                      "composition", "dominant_class"}


def test_bank_has_iwahashi_pike_block_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((48, 48), amplitude=1.0, seed=43))
    bank = descriptors.descriptor_bank(z)
    assert "iwahashi_pike" in bank

    ip = bank["iwahashi_pike"]
    assert set(ip) == IWAHASHI_PIKE_KEYS, set(ip)
    for key in ("slope_mean", "convexity_mean", "texture_mean"):
        assert type(ip[key]) is float, (key, type(ip[key]))
    comp = ip["composition"]
    assert set(comp) == {str(c) for c in range(8)}, set(comp)
    assert all(type(k) is str for k in comp)
    assert all(type(v) is float for v in comp.values()), comp
    assert abs(sum(comp.values()) - 1.0) < 1e-9, sum(comp.values())
    assert type(ip["dominant_class"]) is int and 0 <= ip["dominant_class"] <= 7

    # the bank's block is exactly the source-module signature (bank dx=1.0)
    assert ip == iwahashi_pike.iwahashi_pike_signature(z, dx=1.0)

    # the whole extended bank still serialises, round-trips and is deterministic
    assert json.loads(json.dumps(bank))
    assert descriptors.descriptor_bank(z) == bank


def test_bank_iwahashi_pike_plane_mostly_one_class_rough_spreads():
    # a homogeneous tilted plane collapses to a single terrain class; a seeded
    # rough field spreads mass across several classes (analysis layer only).
    plane = synthetic.plane((60, 60), slope_x=0.2, slope_y=0.1)
    rough = plane + synthetic.rough_field((60, 60), amplitude=1.5, seed=47)
    comp_p = descriptors.descriptor_bank(plane)["iwahashi_pike"]["composition"]
    comp_r = descriptors.descriptor_bank(rough)["iwahashi_pike"]["composition"]
    assert max(comp_p.values()) > 0.95, comp_p          # plane ~ one class
    n_classes_rough = sum(1 for v in comp_r.values() if v > 0.0)
    assert n_classes_rough >= 4, comp_r                 # rough terrain spreads


# --- surface-dissection (depression-filled D8 flow) block wired into the bank --

DRAINAGE_KEYS = {"channel_fraction", "mean_log_acc", "max_acc_fraction",
                 "drainage_density_proxy"}


def test_bank_has_drainage_block_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((48, 48), amplitude=1.0, seed=51))
    bank = descriptors.descriptor_bank(z)
    assert "drainage" in bank

    dr = bank["drainage"]
    assert set(dr) == DRAINAGE_KEYS, set(dr)
    assert all(type(v) is float for v in dr.values()), dr
    assert all(np.isfinite(v) for v in dr.values()), dr
    assert 0.0 < dr["max_acc_fraction"] <= 1.0, dr["max_acc_fraction"]

    # the bank's block is exactly the source-module signature (bank dx=1.0)
    assert dr == drainage.drainage_signature(z, dx=1.0)

    # the whole extended bank still serialises, round-trips and is deterministic
    assert json.loads(json.dumps(bank))
    assert descriptors.descriptor_bank(z) == bank


def test_bank_drainage_dissection_rough_vs_smooth_plane():
    # roughness reorganises drainage: a seeded rough surface concentrates flow
    # more (higher max_acc_fraction) and routes less organised accumulation
    # (lower mean_log_acc) than a smooth tilted plane (analysis layer only).
    plane = synthetic.plane((60, 60), slope_x=0.2, slope_y=0.1)
    rough = plane + synthetic.rough_field((60, 60), amplitude=1.5, seed=53)
    dp = descriptors.descriptor_bank(plane)["drainage"]
    dr = descriptors.descriptor_bank(rough)["drainage"]
    assert dr["max_acc_fraction"] > dp["max_acc_fraction"], (dr, dp)
    assert dr["mean_log_acc"] < dp["mean_log_acc"], (dr, dp)


# --- fractal / lacunarity / entropy / slope-area blocks wired into the bank ---

FRACTAL_KEYS = {"box_count_dimension", "r2", "n_scales"}
LACUNARITY_KEYS = {"lacunarity_r2", "lacunarity_mean", "lacunarity_loglog_slope"}
ENTROPY_KEYS = {"slope_entropy", "elevation_entropy",
                "slope_entropy_norm", "elevation_entropy_norm"}
SLOPE_AREA_KEYS = {"flint_theta", "r2", "log_ks", "n_bins_used"}


def test_bank_has_fractal_lacunarity_entropy_slope_area_blocks_and_json():
    z = (synthetic.plane((48, 48), slope_x=0.2, slope_y=0.1)
         + synthetic.rough_field((48, 48), amplitude=1.0, seed=57))
    bank = descriptors.descriptor_bank(z)
    for key in ("fractal", "lacunarity", "entropy", "slope_area"):
        assert key in bank, key

    fr = bank["fractal"]
    assert set(fr) == FRACTAL_KEYS, set(fr)
    assert type(fr["box_count_dimension"]) is float and type(fr["r2"]) is float
    assert type(fr["n_scales"]) is int, type(fr["n_scales"])
    assert 2.0 <= fr["box_count_dimension"] <= 3.0, fr

    lac = bank["lacunarity"]
    assert set(lac) == LACUNARITY_KEYS, set(lac)
    assert all(type(v) is float for v in lac.values()), lac
    assert lac["lacunarity_r2"] >= 1.0 - 1e-9, lac       # Lambda(r) >= 1 always

    en = bank["entropy"]
    assert set(en) == ENTROPY_KEYS, set(en)
    assert all(type(v) is float for v in en.values()), en
    assert all(np.isfinite(v) and v >= 0.0 for v in en.values()), en

    sa = bank["slope_area"]
    assert set(sa) == SLOPE_AREA_KEYS, set(sa)
    for key in ("flint_theta", "r2", "log_ks"):
        assert type(sa[key]) is float, (key, type(sa[key]))
    assert type(sa["n_bins_used"]) is int, type(sa["n_bins_used"])

    # each bank block is exactly the source-module signature (bank dx=1.0)
    assert fr == fractal.fractal_signature(z)
    assert lac == lacunarity.lacunarity_signature(z)
    assert en == entropy_terrain.entropy_signature(z, dx=1.0)
    assert sa == slope_area.slope_area_signature(z, dx=1.0)

    # the whole extended bank still serialises, round-trips and is deterministic
    assert json.loads(json.dumps(bank))
    assert descriptors.descriptor_bank(z) == bank


def test_bank_fractal_entropy_rough_gt_plane_and_constant_degenerate():
    # a seeded rough field is more complex / diverse than a smooth tilted plane:
    # higher box-counting dimension and higher slope entropy. A constant field is
    # degenerate: fractal dimension exactly 2.0, slope entropy exactly 0 and
    # gliding-box lacunarity exactly 1.0 (analysis layer only -- no decision).
    plane = synthetic.plane((64, 64), slope_x=0.05, slope_y=0.02)
    rough = plane + synthetic.rough_field((64, 64), amplitude=2.0, seed=63)
    bp = descriptors.descriptor_bank(plane)
    br = descriptors.descriptor_bank(rough)
    assert br["fractal"]["box_count_dimension"] > bp["fractal"]["box_count_dimension"], (
        br["fractal"], bp["fractal"])
    assert br["entropy"]["slope_entropy"] > bp["entropy"]["slope_entropy"], (
        br["entropy"], bp["entropy"])
    const = descriptors.descriptor_bank(synthetic.constant((64, 64), 7.0))
    assert const["fractal"]["box_count_dimension"] == 2.0, const["fractal"]
    assert const["entropy"]["slope_entropy"] == 0.0, const["entropy"]
    assert abs(const["lacunarity"]["lacunarity_r2"] - 1.0) < 1e-9, const["lacunarity"]


def test_bank_slope_area_concave_positive_theta():
    # a concave surface z = c*(D - x)^2 flattens as contributing area grows, so
    # the Flint (1974) slope-area concavity index is positive with a decent fit.
    n = 64
    j = np.indices((n, n))[1].astype(float)
    z = 0.02 * (float(n) - j) ** 2
    sa = descriptors.descriptor_bank(z)["slope_area"]
    assert sa["flint_theta"] > 0.0, sa
    assert sa["r2"] > 0.3, sa

