"""Feature fixtures with known analytic answers."""
import numpy as np
from terratrace import synthetic, features


def test_slope_of_plane_matches_analytic():
    a, b, dx, dy = 0.2, 0.1, 2.0, 2.0
    z = synthetic.plane((20, 20), slope_x=a, slope_y=b, dx=dx, dy=dy)
    expected = np.degrees(np.arctan(np.hypot(a, b)))
    got = features.slope_deg(z, dx, dy)
    assert np.allclose(got, expected, atol=1e-9), (got.mean(), expected)


def test_relief_of_ramp_is_exact_with_alpha_zero():
    k, window = 3.0, 3
    z = synthetic.ramp_x((9, 9), rise_per_pixel=k)
    r = features.relief(z, window=window, alpha=0.0)
    assert np.allclose(r, k * (window - 1)), r.mean()


def test_ruggedness_of_plane_is_zero():
    z = synthetic.plane((15, 15), slope_x=0.3, slope_y=0.1, dx=1.0, dy=1.0)
    rug = features.ruggedness(z, window=5, dx=1.0, dy=1.0)
    assert np.nanmax(np.abs(rug)) < 1e-9, np.nanmax(np.abs(rug))


def test_ruggedness_offset_invariant_and_scale_linear():
    z = synthetic.gaussian_hill((21, 21), amplitude=8.0, sigma=4.0)
    base = features.ruggedness(z, window=5)
    offset = features.ruggedness(z + 100.0, window=5)
    scaled = features.ruggedness(2.0 * z, window=5)
    assert np.allclose(base, offset, atol=1e-9)
    assert np.allclose(scaled, 2.0 * base, atol=1e-6)


def test_connectivity_counts_largest_component():
    slope = np.full((5, 5), 90.0)
    slope[0:3, 0:3] = 5.0   # 9-cell connected block
    slope[4, 4] = 5.0        # isolated single cell
    frac, largest = features.low_slope_connectivity(slope, threshold_deg=10.0)
    assert largest == 9, largest
    assert abs(frac - 9 / 25) < 1e-12, frac


def test_aspect_dispersion_plane_is_zero_and_noise_high():
    plane = synthetic.plane((40, 40), slope_x=0.2, slope_y=0.1)
    assert features.aspect_dispersion(plane) < 1e-6
    noise = synthetic.rough_field((60, 60), amplitude=1.0, seed=7)
    assert features.aspect_dispersion(noise) > 0.5


def test_hypsometric_integral_ramp_is_half_and_flat_is_nan():
    ramp = synthetic.ramp_x((10, 10), rise_per_pixel=3.0)
    assert abs(features.hypsometric_integral(ramp) - 0.5) < 1e-9
    flat = synthetic.constant((10, 10), value=5.0)
    assert np.isnan(features.hypsometric_integral(flat))
