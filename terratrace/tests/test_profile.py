"""Data-health profile fixtures (dependency-free, assert-based)."""
import numpy as np

from terratrace import profile


def test_smooth_ramp_clean():
    z = np.tile(np.arange(10.0), (10, 1))        # 10x10, columns run 0..9
    prof = profile.profile_dem(z)
    assert prof["valid_fraction"] == 1.0
    assert prof["relief"] > 0.0
    assert prof["water_fraction"] < 0.2          # only the single zero column
    assert prof["p1"] <= prof["p50"] <= prof["p99"]
    out = profile.summarize(z)
    assert out["flags"] == []
    assert out["ok"] is True


def test_water_contamination_blocks():
    z = np.zeros((10, 10))
    z.flat[:20] = 1.0                            # 80 exact zeros, 20 positive
    prof = profile.profile_dem(z)
    assert abs(prof["water_fraction"] - 0.8) < 1e-9
    out = profile.summarize(z)
    assert "WATER_CONTAMINATION" in out["flags"]
    assert out["ok"] is False


def test_all_nan():
    z = np.full((5, 5), np.nan)
    out = profile.summarize(z)
    assert "ALL_NAN" in out["flags"]
    assert out["ok"] is False
    assert out["profile"]["n_valid"] == 0
    assert np.isnan(out["profile"]["min"])
    assert np.isnan(out["profile"]["max"])


def test_constant_array_advisory_only():
    z = np.full((8, 8), 5.0)
    out = profile.summarize(z)
    assert "SUSPICIOUS_CONSTANT" in out["flags"]
    assert "DEGENERATE_RELIEF" in out["flags"]
    assert out["profile"]["water_fraction"] == 0.0   # 5.0 is not near sea level
    assert out["ok"] is True                         # advisory flags don't block


def test_low_valid_fraction_blocks():
    z = np.arange(100.0).reshape(10, 10)
    z.flat[:70] = np.nan                         # ~70% nodata -> 30% valid
    out = profile.summarize(z)
    assert "LOW_VALID_FRACTION" in out["flags"]
    assert out["ok"] is False


def test_profile_is_deterministic():
    z = np.arange(25.0).reshape(5, 5)            # all finite -> no NaN in dict
    assert profile.profile_dem(z) == profile.profile_dem(z)
