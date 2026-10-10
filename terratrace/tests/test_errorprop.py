"""Analytic elevation-error-propagation checks (dependency-free, deterministic)."""
import math

from terratrace import errorprop, catalog


def test_zero_sigma_z_gives_zero_everywhere():
    out = errorprop.propagate_feature_uncertainty(0.0, dx=30.0, median_slope_deg=10.0)
    assert out["slope_sigma_deg"] == 0.0, out
    assert out["relief_sigma_m"] == 0.0, out
    assert out["ruggedness_sigma_m"] == 0.0, out
    assert errorprop.slope_sigma_deg(0.0, 30.0, 20.0) == 0.0
    assert errorprop.relief_sigma_m(0.0) == 0.0
    assert errorprop.ruggedness_sigma_m(0.0) == 0.0


def test_slope_sigma_grows_with_sigma_z_and_shrinks_with_dx():
    small = errorprop.slope_sigma_deg(2.0, 30.0)
    big = errorprop.slope_sigma_deg(6.0, 30.0)
    assert big > small > 0.0, (small, big)
    coarse = errorprop.slope_sigma_deg(4.0, 90.0)
    fine = errorprop.slope_sigma_deg(4.0, 30.0)
    assert fine > coarse > 0.0, (fine, coarse)


def test_relief_sigma_grows_with_sigma_z():
    assert errorprop.relief_sigma_m(6.0) > errorprop.relief_sigma_m(2.0) > 0.0


def test_relief_sigma_is_exact_sqrt2():
    for s in (0.0, 0.2, 4.0, 9.0, 100.0):
        assert abs(errorprop.relief_sigma_m(s) - math.sqrt(2.0) * s) < 1e-12, s


def test_slope_sigma_flat_matches_closed_form():
    for s, dx in ((4.0, 30.0), (0.2, 1.0), (9.0, 90.0)):
        expected = math.degrees(s / (dx * math.sqrt(2.0)))
        assert abs(errorprop.slope_sigma_deg(s, dx, 0.0) - expected) < 1e-9, (s, dx)


def test_steeper_slope_gives_smaller_angle_sigma():
    s, dx = 4.0, 30.0
    flat = errorprop.slope_sigma_deg(s, dx, 0.0)
    steep = errorprop.slope_sigma_deg(s, dx, 45.0)
    assert flat > steep > 0.0, (flat, steep)


def test_for_source_matches_catalog_and_orders_by_accuracy():
    out = errorprop.for_source("earth_cop30", dx=30.0)
    assert out["source_id"] == "earth_cop30"
    assert out["vertical_accuracy_m"] == catalog.vertical_accuracy_for("earth_cop30")
    assert out["slope_sigma_deg"] > 0.0, out
    accurate = errorprop.for_source("earth_usgs1m", dx=30.0)["slope_sigma_deg"]
    noisy = errorprop.for_source("earth_srtmgl3", dx=30.0)["slope_sigma_deg"]
    assert accurate < noisy, (accurate, noisy)


def test_propagate_returns_all_documented_keys():
    out = errorprop.propagate_feature_uncertainty(4.0, dx=30.0, median_slope_deg=5.0)
    assert set(out) == {"sigma_z", "dx", "slope_sigma_deg",
                        "relief_sigma_m", "ruggedness_sigma_m"}, set(out)
    assert out["sigma_z"] == 4.0 and out["dx"] == 30.0
