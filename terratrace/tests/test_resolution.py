"""Analytic + frozen ground-truth tests for source-resolution matching.

The analytic tests pin the filter to closed-form behaviour (a constant is a fixed
point up to the border; a sinusoid of wavelength L is attenuated by exactly
exp(-2 pi^2 sigma^2 / L^2); NaN never bleeds; quadrature kernel arithmetic).

The ground-truth oracle is EMPIRICAL METHOD VALIDATION (that the control removes a
planted source-smoothing artifact), NOT a scientific finding about Mars.

GROUND TRUTH (fixed, first-principles). Terrain is red-spectrum spectral synthesis
(amplitude ~ (k^2 + k0^2)^(-beta/2), random phases, fixed seeds), not white noise.

  * ``mars``       -- terrain T (beta 1.8, 120 m RMS) seen through a coarse
                      instrument: Gaussian-smoothed to FWHM 1400 m, then point-
                      sampled at 450 m posting (declared effective res 3x = 1350 m).
  * ``B_twin``     -- an independent realisation with the SAME spectrum as T at
                      30 m: the morphologically correct analog, by construction.
  * ``A_impostor`` -- a genuinely smoother terrain (steeper falloff, beta 2.6, same
                      RMS) at 30 m: a wrong analog, by construction.

At a 450 m support (below the reference's 1350 m effective resolution; realised
support is exactly 450 m for every unit: Mars factor 1, Earth factor 15) the
interpolation-smooth reference looks like the smooth impostor, so WITHOUT matching
A_impostor is recommended (the artifact). WITH ``match_effective_resolution`` the
30 m units are degraded to 1350 m first and B_twin is recommended. A perfect-
instrument control (reference observed at 30 m, unsmoothed) already picks B_twin
raw -- so the artifact is caused by the source smoothing, nothing else. The flip
was checked on 6 seed triples during exploration; 3 are frozen here.

Dependency-free: plain ``def test_*()``, assert-based, no pytest, no network.
"""
import functools
import json
import time

import numpy as np

from terratrace import decision, matched_benchmark as mb, resolution as res, study

_N = 1500                    # 30 m grid -> 45 km side
_DX = 30.0
_DEC = 15                    # 30 m * 15 = 450 m reference posting
_MARS_DX = _DX * _DEC
_INSTRUMENT_FWHM_M = 1400.0  # true reference resolving power (> grid spacing)
_K0 = 1.0 / 20000.0          # long-wavelength roll-off (cycles / m)
_BETA_TERRAIN = 1.8
_BETA_SMOOTH = 2.6
_RMS_M = 120.0
_EXTENT_M = 36000.0
_SUPPORT_M = 450.0
_SEEDS = (11, 22, 33)        # (reference T, twin B, impostor A)


def _terrain(beta, rms_m, seed, instrument_fwhm_m=None):
    """Red-spectrum terrain by FFT spectral synthesis on the 30 m grid. White
    noise is shaped by (k^2 + k0^2)^(-beta/2) and scaled to ``rms_m`` BEFORE any
    instrument MTF, so a smoothed and an unsmoothed field share one spectrum. The
    instrument is an exact (periodic) Gaussian MTF -- independent of the filter
    under test."""
    rng = np.random.default_rng(seed)
    spec = np.fft.rfft2(rng.standard_normal((_N, _N)))
    ky = np.fft.fftfreq(_N, d=_DX)[:, None]
    kx = np.fft.rfftfreq(_N, d=_DX)[None, :]
    k2 = kx * kx + ky * ky
    amp = (k2 + _K0 * _K0) ** (-beta / 2.0)
    amp[0, 0] = 0.0
    amp /= np.sqrt((amp * amp).mean())
    if instrument_fwhm_m:
        s = res.fwhm_to_sigma(instrument_fwhm_m)
        amp = amp * np.exp(-2.0 * np.pi ** 2 * s * s * k2)
    return rms_m * np.fft.irfft2(spec * amp, s=(_N, _N))


@functools.lru_cache(maxsize=None)
def _scene(seeds=_SEEDS):
    """The frozen scene; arrays are read-only so any mutation raises."""
    t_seed, b_seed, a_seed = seeds
    units = {
        "mars": _terrain(_BETA_TERRAIN, _RMS_M, t_seed,
                         _INSTRUMENT_FWHM_M)[_DEC // 2::_DEC, _DEC // 2::_DEC],
        "A_impostor": _terrain(_BETA_SMOOTH, _RMS_M, a_seed),
        "B_twin": _terrain(_BETA_TERRAIN, _RMS_M, b_seed),
    }
    for z in units.values():
        z.setflags(write=False)
    return units


_SPACINGS = {"mars": _MARS_DX, "A_impostor": _DX, "B_twin": _DX}


def _core_vectors(units, spacings):
    """Core-lens distance vectors (slope, relief, ruggedness, connectivity) to the
    reference, on the SAME crops/support matched_cell uses."""
    cropped = {u: mb.crop_center(z, spacings[u], _EXTENT_M)[0] for u, z in units.items()}
    pkg = study.compare_units(cropped, {u: "verified_allowed" for u in units}, spacings,
                              reference_id="mars", target_support_m=_SUPPORT_M,
                              decision_metrics="core")
    return pkg["baseline_vectors"]


def _sinusoid_amplitude(z):
    """Amplitude of a pure sinusoid from its RMS over an integer number of periods."""
    return float(np.sqrt(2.0 * np.mean(z ** 2)))


# --------------------------------------------------------------------------- #
# Analytic                                                                     #
# --------------------------------------------------------------------------- #

def test_fwhm_to_sigma_closed_form():
    assert abs(res.fwhm_to_sigma(2.0 * np.sqrt(2.0 * np.log(2.0))) - 1.0) < 1e-12
    assert abs(res.fwhm_to_sigma(1350.0) - 573.29) < 0.01


def test_constant_field_stays_constant_including_edges():
    z = np.full((180, 250), 7.25)
    for sigma in (0.7, 4.0, 19.5):
        out = res.gaussian_filter_nan(z, sigma)
        assert out.shape == z.shape
        assert np.max(np.abs(out - 7.25)) < 1e-9, sigma          # border included
        assert np.max(np.abs(out[0, :] - 7.25)) < 1e-9 and np.max(np.abs(out[:, -1] - 7.25)) < 1e-9
    zr = np.random.default_rng(3).standard_normal((300, 300)) + 10.0
    out = res.gaussian_filter_nan(zr, 5.0)
    assert abs(out.mean() - zr.mean()) < 5e-3, (out.mean(), zr.mean())
    assert out.std() < 0.2 * zr.std()                             # it does low-pass


def test_sinusoid_attenuation_matches_gaussian_transfer():
    wavelength = 40.0
    x = np.arange(400)
    z = np.tile(np.sin(2.0 * np.pi * x / wavelength), (200, 1))   # varies along x only
    for sigma in (2.0, 5.0, 8.0):
        out = res.gaussian_filter_nan(z, sigma)
        interior = out[50:-50, 60:340]                            # 7 whole periods
        ratio = _sinusoid_amplitude(interior) / _sinusoid_amplitude(z[50:-50, 60:340])
        expected = np.exp(-2.0 * np.pi ** 2 * sigma ** 2 / wavelength ** 2)
        assert abs(ratio / expected - 1.0) < 0.05, (sigma, ratio, expected)


def test_nan_safety_and_all_nan():
    rng = np.random.default_rng(7)
    z = rng.standard_normal((120, 140))
    z[30:45, 60:90] = np.nan
    z[0, :] = np.nan
    z[77, 13] = np.nan
    before = z.copy()
    out = res.gaussian_filter_nan(z, 6.0)
    nan_in = np.isnan(z)
    assert np.array_equal(np.isnan(out), nan_in)                 # NaN stays NaN, nothing else
    assert np.all(np.isfinite(out[~nan_in]))
    assert np.array_equal(np.isnan(before), nan_in) and np.allclose(before[~nan_in], z[~nan_in])
    allnan = res.gaussian_filter_nan(np.full((9, 11), np.nan), 3.0)
    assert allnan.shape == (9, 11) and np.all(np.isnan(allnan))
    same = res.gaussian_filter_nan(z, 0.0)                       # sigma <= 0 -> copy
    assert same is not z and np.array_equal(np.isnan(same), nan_in)
    assert np.allclose(same[~nan_in], z[~nan_in])


def test_identity_when_target_not_finer_than_own():
    z = np.random.default_rng(1).standard_normal((50, 50))
    for target in (90.0, 60.0):                                  # own = 3 * 30 = 90
        out, info = res.emulate_effective_resolution(z, 30.0, target)
        assert info["smoothed"] is False and info["kernel_fwhm_m"] == 0.0
        assert info["own_fwhm_m"] == mb.effective_resolution_m(30.0)
        assert out is not z and np.array_equal(out, z)
    out, info = res.emulate_effective_resolution(z, 30.0, 150.0)  # quadrature: sqrt(150^2-90^2)=120
    assert info["smoothed"] is True and abs(info["kernel_fwhm_m"] - 120.0) < 1e-9
    assert abs(info["sigma_px"] - res.fwhm_to_sigma(120.0) / 30.0) < 1e-12
    assert out.std() < z.std()


def test_match_effective_resolution_coarse_untouched_fine_smoothed():
    rng = np.random.default_rng(5)
    coarse = rng.standard_normal((60, 60)) * 40.0
    fine = rng.standard_normal((600, 600)) * 40.0
    grids = {"coarse": coarse, "fine": fine}
    snap = {k: v.copy() for k, v in grids.items()}
    out, report = res.match_effective_resolution(grids, {"coarse": 300.0, "fine": 30.0})
    assert report["target_fwhm_m"] == 900.0                      # max(3*300, 3*30)
    assert report["units"]["coarse"]["smoothed"] is False
    assert np.array_equal(out["coarse"], coarse) and out["coarse"] is not coarse
    assert report["units"]["fine"]["smoothed"] is True
    assert out["fine"].std() < 0.1 * fine.std()
    for k in grids:                                              # inputs not mutated
        assert np.array_equal(grids[k], snap[k])
    assert json.loads(json.dumps(report)) == report
    same, rep2 = res.match_effective_resolution({"a": coarse, "b": coarse}, 30.0)
    assert all(not u["smoothed"] for u in rep2["units"].values())  # scalar spacing, all equal
    assert np.array_equal(same["a"], coarse)


def test_speed_1500_grid_sigma_20():
    z = np.random.default_rng(0).standard_normal((1500, 1500))
    t0 = time.perf_counter()
    out = res.gaussian_filter_nan(z, 20.0)
    elapsed = time.perf_counter() - t0
    assert out.shape == z.shape and np.all(np.isfinite(out))
    assert elapsed < 5.0, elapsed


# --------------------------------------------------------------------------- #
# Ground-truth oracle: a planted source-smoothing artifact                    #
# --------------------------------------------------------------------------- #

def test_oracle_ground_truth_is_well_posed():
    # The impostor is GENUINELY smoother than the twin at native 30 m (not just
    # after aggregation) -- otherwise "wrong analog" would not be a ground truth.
    scene = _scene()
    def mean_slope_deg(z, dx):
        gy, gx = np.gradient(z, dx)
        return float(np.degrees(np.arctan(np.hypot(gx, gy))).mean())
    assert mean_slope_deg(scene["A_impostor"], _DX) < 0.5 * mean_slope_deg(scene["B_twin"], _DX)
    assert scene["mars"].shape == (_N // _DEC, _N // _DEC)
    assert _SUPPORT_M < mb.effective_resolution_m(_MARS_DX)       # below ref's eff. res


def test_oracle_artifact_without_matching_and_recovery_with_matching():
    scene = _scene()
    raw = mb.matched_cell(scene, _SPACINGS, "mars", _EXTENT_M, _SUPPORT_M,
                          decision_metrics="core")
    raw_v = _core_vectors(scene, _SPACINGS)
    # WITHOUT resolution matching: the smoothing artifact picks the impostor.
    assert raw["recommended_unit"] == "A_impostor", raw
    assert decision.dominates(raw_v["A_impostor"], raw_v["B_twin"]), raw_v

    matched_grids, report = res.match_effective_resolution(scene, _SPACINGS)
    assert report["target_fwhm_m"] == 1350.0
    assert report["units"]["mars"]["smoothed"] is False
    assert report["units"]["A_impostor"]["smoothed"] and report["units"]["B_twin"]["smoothed"]
    assert np.array_equal(matched_grids["mars"], scene["mars"])
    fixed = mb.matched_cell(matched_grids, _SPACINGS, "mars", _EXTENT_M, _SUPPORT_M,
                            decision_metrics="core")
    fixed_v = _core_vectors(matched_grids, _SPACINGS)
    # WITH resolution matching: the true twin is recovered, on every core axis.
    assert fixed["recommended_unit"] == "B_twin", fixed
    assert fixed["result_state"] == "RECOMMEND_FOLLOW_UP"
    assert decision.dominates(fixed_v["B_twin"], fixed_v["A_impostor"]), fixed_v
    # Mechanism: the twin's slope distance collapses once resolving power matches.
    assert raw_v["B_twin"][0] > 4.0 * fixed_v["B_twin"][0], (raw_v, fixed_v)


def test_oracle_perfect_instrument_control_has_no_artifact():
    # Same terrain T observed WITHOUT the coarse instrument (30 m, unsmoothed): the
    # raw comparison already recovers the twin -> the artifact above is caused by
    # source smoothing, not by the candidates or the decision machinery.
    scene = _scene()
    perfect = dict(scene)
    perfect["mars"] = _terrain(_BETA_TERRAIN, _RMS_M, _SEEDS[0])
    cell = mb.matched_cell(perfect, _DX, "mars", _EXTENT_M, _SUPPORT_M,
                           decision_metrics="core")
    assert cell["recommended_unit"] == "B_twin", cell


def test_oracle_flip_is_not_a_lucky_seed():
    for seeds in ((1, 2, 3), (42, 43, 44)):
        scene = _scene(seeds)
        raw = mb.matched_cell(scene, _SPACINGS, "mars", _EXTENT_M, _SUPPORT_M)
        grids, _ = res.match_effective_resolution(scene, _SPACINGS)
        fixed = mb.matched_cell(grids, _SPACINGS, "mars", _EXTENT_M, _SUPPORT_M)
        assert raw["recommended_unit"] == "A_impostor", (seeds, raw)
        assert fixed["recommended_unit"] == "B_twin", (seeds, fixed)


def test_default_study_hash_unchanged_by_this_module():
    # Additive module: it must not perturb the gated default study.
    h = study.run_study()["package_hash"]
    assert len(h) == 64 and all(ch in "0123456789abcdef" for ch in h)
    assert study.run_study()["package_hash"] == h
