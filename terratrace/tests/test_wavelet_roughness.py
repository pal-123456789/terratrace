"""Tests for the 2-D orthonormal Haar wavelet multiscale-roughness descriptor
(``terratrace.wavelet_roughness``). Dependency-free: plain ``def test_*()``,
assert-based, no pytest, no network -- small synthetic surfaces with analytic
answers, mirroring the style of test_spectral.py / test_kh_roughness.py.
"""
import json

import numpy as np

from terratrace import wavelet_roughness


def test_constant_zero_detail():
    # A flat field has no scale-to-scale contrast -> every detail coefficient is
    # zero, so the total detail energy vanishes and no level dominates.
    z = np.full((64, 64), 3.5)
    sig = wavelet_roughness.wavelet_signature(z)
    assert sig["total_detail_energy"] < 1e-9, sig["total_detail_energy"]
    assert sig["dominant_level"] == 0, sig


def test_parseval_energy_conserved():
    # Orthonormal transform -> sum of all level detail energies plus the squared
    # final approximation equals sum(z**2). 64x64 is dyadic, so this is exact.
    rng = np.random.default_rng(2024)
    z = rng.standard_normal((64, 64))
    z = z - z.mean()
    levels, final_approx = wavelet_roughness.haar_transform(z)
    detail = sum(lv["detail_energy"] for lv in levels)
    approx = float(np.sum(final_approx ** 2))
    total = float(np.sum(z ** 2))
    rel = abs(detail + approx - total) / total
    assert rel < 1e-6, rel


def test_checkerboard_finest_dominant():
    # A period-2 (+/-1) checkerboard is pure finest-scale structure: all of its
    # energy sits in the diagonal detail at level 1.
    i, j = np.indices((64, 64))
    z = np.where((i + j) % 2 == 0, 1.0, -1.0)
    sig = wavelet_roughness.wavelet_signature(z)
    assert sig["dominant_level"] == 1, sig
    assert sig["energy_by_level"]["1"] > 0.999, sig["energy_by_level"]


def test_coarse_pattern_coarser_than_fine():
    # A 16x16-block (+/-1) pattern has its contrast at a coarser scale than the
    # period-2 checkerboard, so its dominant detail level is strictly larger.
    i, j = np.indices((64, 64))
    fine = np.where((i + j) % 2 == 0, 1.0, -1.0)
    block = 16
    coarse = np.where(((i // block) + (j // block)) % 2 == 0, 1.0, -1.0)
    fine_dom = wavelet_roughness.wavelet_signature(fine)["dominant_level"]
    coarse_dom = wavelet_roughness.wavelet_signature(coarse)["dominant_level"]
    assert fine_dom == 1, fine_dom
    assert coarse_dom > fine_dom, (coarse_dom, fine_dom)


def test_signature_contract():
    rng = np.random.default_rng(7)
    z = rng.standard_normal((64, 64))
    sig = wavelet_roughness.wavelet_signature(z)
    assert set(sig) == {"energy_by_level", "dominant_level",
                        "total_detail_energy", "detail_loglog_slope"}, set(sig)
    assert isinstance(sig["energy_by_level"], dict)
    assert all(isinstance(k, str) for k in sig["energy_by_level"])
    assert all(isinstance(v, float) for v in sig["energy_by_level"].values())
    assert isinstance(sig["dominant_level"], int)
    assert isinstance(sig["total_detail_energy"], float)
    assert isinstance(sig["detail_loglog_slope"], float)
    # fractions sum to ~1 when detail energy exists
    assert sig["total_detail_energy"] > 0.0
    assert abs(sum(sig["energy_by_level"].values()) - 1.0) < 1e-9, sig["energy_by_level"]
    dumped = json.dumps(sig)                                 # JSON-serialisable
    assert isinstance(dumped, str) and json.loads(dumped)
    assert wavelet_roughness.wavelet_signature(z) == sig     # deterministic


def test_nan_safe():
    # A few NaNs are filled with the finite mean -> no raise, finite outputs.
    rng = np.random.default_rng(99)
    z = rng.standard_normal((48, 48))
    z[5, 5] = np.nan
    z[20, 30] = np.nan
    z[40, 2] = np.nan
    levels, final_approx = wavelet_roughness.haar_transform(z)
    assert levels and all(np.isfinite(lv["detail_energy"]) for lv in levels)
    assert np.all(np.isfinite(final_approx))
    sig = wavelet_roughness.wavelet_signature(z)
    assert np.isfinite(sig["total_detail_energy"])
    assert isinstance(sig["dominant_level"], int)
    assert json.loads(json.dumps(sig))


def test_haar_levels_contract():
    # Lower-level API shape: finest-first 1-based levels, well-typed dicts, and
    # agreement with the full transform helper. 32x32 is dyadic -> 5 levels.
    rng = np.random.default_rng(3)
    z = rng.standard_normal((32, 32))
    levels = wavelet_roughness.haar_levels(z)
    assert isinstance(levels, list) and levels
    assert [lv["level"] for lv in levels] == list(range(1, len(levels) + 1))
    for lv in levels:
        assert set(lv) == {"level", "detail_energy", "n_coeffs"}, set(lv)
        assert isinstance(lv["level"], int)
        assert isinstance(lv["detail_energy"], float) and lv["detail_energy"] >= 0.0
        assert isinstance(lv["n_coeffs"], int) and lv["n_coeffs"] > 0
    assert wavelet_roughness.haar_transform(z)[0] == levels   # consistent
    assert len(levels) == 5, len(levels)                      # 32->16->8->4->2->1
    assert levels[0]["n_coeffs"] == 3 * 16 * 16               # 3 * (16x16) blocks
