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
    assert abs(features.hypsometric_integral(ramp) - 0.5) < 0.1
    flat = synthetic.constant((10, 10), value=5.0)
    assert np.isnan(features.hypsometric_integral(flat))


def test_aspect_dispersion_flat_is_zero_not_noise():
    flat = synthetic.constant((30, 30), value=7.0)
    assert features.aspect_dispersion(flat) == 0.0


def test_tpi_dispersion_zero_on_plane_positive_on_hill():
    plane = synthetic.plane((21, 21), slope_x=0.3, slope_y=0.1)
    assert features.tpi_dispersion(plane, window=5) < 1e-9
    hill = synthetic.gaussian_hill((31, 31), amplitude=12.0, sigma=5.0)
    assert features.tpi_dispersion(hill, window=5) > 0.0


def test_small_aoi_features_degrade_gracefully():
    tiny = synthetic.plane((3, 3), slope_x=0.1)
    assert np.all(np.isnan(features.relief(tiny, window=5)))
    assert np.all(np.isnan(features.ruggedness(tiny, window=5)))
    assert np.isnan(features.tpi_dispersion(tiny, window=5))


# --- geomorphometric descriptor depth (curvature / VRM / roughness) ---------

def _paraboloid(n=41, a=0.001, L=1.0):
    c = (n - 1) / 2.0
    ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
    x = (jj - c) * L
    y = (ii - c) * L
    return a * (x * x + y * y)


def _median_finite(arr):
    v = np.asarray(arr, dtype=float)
    v = v[np.isfinite(v)]
    return float(np.median(v))


def test_curvatures_zero_on_plane():
    plane = synthetic.plane((21, 21), slope_x=0.2, slope_y=0.1, dx=1.0, dy=1.0)
    for f in (features.profile_curvature, features.plan_curvature, features.mean_curvature):
        m = f(plane, dx=1.0)
        assert np.nanmax(np.abs(m)) < 1e-9, (f.__name__, np.nanmax(np.abs(m)))


def test_curvatures_match_paraboloid_analytic():
    # z = a(x^2+y^2): profile=-2a, plan=+2a, mean=-4a (exact for a 3x3 ZT fit).
    a, L = 0.001, 1.0
    z = _paraboloid(a=a, L=L)
    assert abs(_median_finite(features.profile_curvature(z, L)) - (-2 * a)) < 1e-6
    assert abs(_median_finite(features.plan_curvature(z, L)) - (2 * a)) < 1e-6
    assert abs(_median_finite(features.mean_curvature(z, L)) - (-4 * a)) < 1e-9


def test_vrm_zero_on_plane_and_rises_with_roughness():
    plane = synthetic.plane((40, 40), slope_x=0.5, slope_y=0.2, dx=1.0, dy=1.0)
    assert _median_finite(features.vector_ruggedness(plane, 3, 1.0, 1.0)) < 1e-9
    vrms = [_median_finite(features.vector_ruggedness(
        plane + synthetic.rough_field((40, 40), amplitude=a, seed=3), 3, 1.0, 1.0))
        for a in (0.0, 0.2, 1.0, 3.0)]
    assert all(vrms[i] < vrms[i + 1] for i in range(len(vrms) - 1)), vrms
    assert 0.0 <= vrms[-1] <= 1.0


def test_structure_function_increases_and_hurst_bounds():
    # A linear ramp has rms difference exactly proportional to lag -> H = 1.
    ramp = synthetic.ramp_x((50, 50), rise_per_pixel=2.0)
    sf = features.structure_function(ramp, lags=(1, 2, 4, 8), dx=1.0)
    vals = [sf[k] for k in sorted(sf)]
    assert all(vals[i] < vals[i + 1] for i in range(len(vals) - 1)), vals
    assert abs(features.hurst_exponent(ramp, lags=(1, 2, 4, 8)) - 1.0) < 1e-6
    # White noise is uncorrelated -> near-zero scaling exponent.
    noise = synthetic.rough_field((80, 80), amplitude=1.0, seed=5)
    assert features.hurst_exponent(noise, lags=(1, 2, 4, 8, 16)) < 0.1


def test_curvature_small_aoi_degrades_gracefully():
    tiny = synthetic.plane((2, 2), slope_x=0.1)
    assert np.all(np.isnan(features.profile_curvature(tiny)))
    assert np.all(np.isnan(features.mean_curvature(tiny)))


# --- added analysis-layer descriptors: SAR / TRI / TPI map / landform mix ----

def test_surface_area_ratio_flat_is_one_and_plane_is_sec_slope():
    flat = synthetic.constant((20, 20), value=5.0)
    sar_flat = features.surface_area_ratio(flat, 1.0, 1.0)
    assert np.allclose(sar_flat, 1.0, atol=1e-12), float(np.nanmax(np.abs(sar_flat - 1.0)))

    a, b, dx, dy = 0.2, 0.1, 2.0, 2.0
    z = synthetic.plane((20, 20), slope_x=a, slope_y=b, dx=dx, dy=dy)
    sar = features.surface_area_ratio(z, dx, dy)
    expected = np.sqrt(1.0 + a * a + b * b)         # = sec(slope) for a tilted plane
    assert np.allclose(sar, expected, atol=1e-6), (float(np.nanmax(sar)), float(expected))
    slope_rad = np.radians(features.slope_deg(z, dx, dy))
    assert np.allclose(sar, 1.0 / np.cos(slope_rad), atol=1e-6)
    assert np.all(sar > 1.0) and np.all(np.isfinite(sar))


def test_terrain_ruggedness_index_zero_on_constant_and_grows_with_roughness():
    const = synthetic.constant((20, 20), value=3.0)
    tri_c = features.terrain_ruggedness_index(const, window=3)
    assert np.nanmax(np.abs(tri_c)) < 1e-12, float(np.nanmax(np.abs(tri_c)))

    # same seed, scaled amplitude -> TRI scales linearly, so rough > smooth.
    smooth = synthetic.rough_field((40, 40), amplitude=0.3, seed=1)
    rough = synthetic.rough_field((40, 40), amplitude=3.0, seed=1)
    tri_s = float(np.nanmean(features.terrain_ruggedness_index(smooth, window=3)))
    tri_r = float(np.nanmean(features.terrain_ruggedness_index(rough, window=3)))
    assert tri_r > tri_s > 0.0, (tri_r, tri_s)


def test_tpi_map_zero_on_plane_nonzero_on_hill_and_matches_dispersion():
    plane = synthetic.plane((21, 21), slope_x=0.3, slope_y=0.1)
    tpi_plane = features.tpi_map(plane, window=5)
    assert np.nanmax(np.abs(tpi_plane)) < 1e-9, float(np.nanmax(np.abs(tpi_plane)))

    hill = synthetic.gaussian_hill((31, 31), amplitude=12.0, sigma=5.0)
    tpi_hill = features.tpi_map(hill, window=5)
    assert np.nanmax(np.abs(tpi_hill)) > 0.0
    finite = tpi_hill[np.isfinite(tpi_hill)]
    # tpi_dispersion is exactly the std of this map's finite values.
    assert abs(float(np.std(finite)) - features.tpi_dispersion(hill, window=5)) < 1e-9


def test_landform_fraction_hill_sums_to_one_flat_degenerate():
    hill = synthetic.gaussian_hill((31, 31), amplitude=12.0, sigma=5.0)
    lf = features.landform_fraction(hill, window=5, k=1.0)
    assert set(lf) == {"ridge", "valley", "flat"}, set(lf)
    assert abs((lf["ridge"] + lf["valley"] + lf["flat"]) - 1.0) < 1e-9, lf
    assert lf["ridge"] + lf["valley"] > 0.0, lf
    assert all(0.0 <= v <= 1.0 for v in lf.values()), lf

    flat = synthetic.constant((20, 20), value=4.0)
    lff = features.landform_fraction(flat, window=5, k=1.0)   # must not raise
    all_flat = abs(lff["flat"] - 1.0) < 1e-9
    degenerate = lff["ridge"] == lff["valley"] == lff["flat"] == 0.0
    assert all_flat or degenerate, lff
