# Feature definitions, units, and claim boundaries

The master plan (§4.4, and release-item “feature definitions and units”) requires every feature to
carry **a definition, a unit, a physical window, a source, and a stated limitation**. This page is
that contract.

Two facts to hold on to. First, the numbers below are the ones the engine actually emits: the table
was written against `descriptors.descriptor_bank()`, which returns **40 descriptor families and 200
scalar outputs** on a single tile — the groupings here are the same groupings the code uses. Second,
**none of these is a traversability, hazard, geologic-equivalence, site-access, or mission-readiness
measurement.** Every row’s right-hand column says what it *cannot* support; that boundary is the
point of the table, not a disclaimer bolted onto it.

Windows are given in the units they are declared in. `dx` is the pixel size of the projected metric
grid in metres; `w` is the moving-window radius in pixels unless a metre figure is stated. All
statistics are quoted as a five-number summary (mean, std, p10, p50, p90) unless a family reports
something else.

## Core morphology — the decision axes

| Family | Outputs (unit) | Definition and window | Citation | Claim boundary |
|---|---|---|---|---|
| Slope | `slope.{mean,std,p10,p50,p90}` (degrees) | Horn/central-difference gradient magnitude of the projected metric grid, `arctan(|∇z|)`; per cell at `dx` | standard DEM practice | Broad morphology. **Not** wheel-scale slope, not vehicle safety |
| Local relief | `relief.{…}` (metres) | Upper − lower quantile of elevation inside a declared physical window (`α=0` → max−min; α=0.05 → P5–P95) | robust relief statistics | Terrain variation at the window. **Not** rock height or obstacle field |
| Detrended ruggedness | `ruggedness.{…}` (metres) | RMS of residuals after removing a local best-fit plane; a perfect plane returns ≈ 0 | — | Relative morphology at support. **Not** mechanical roughness or soil strength |
| Low-slope connectivity | scalar (fraction) | Fraction of valid cells in the largest 4-connected component below a declared slope threshold | O’Callaghan & Mark (1984) | A map-scale corridor statistic. **Not** a route, not traversability |
| Aspect dispersion | `aspect_dispersion` (0–1) | Circular variance of slope azimuth; 0 = one dominant downslope direction, ~1 = isotropic | — | Directional texture. **Not** illumination or wind regime |
| Hypsometric integral | `hypsometric_integral` (0–1) | `(mean − min)/(max − min)`; 0.5 = symmetric area–altitude distribution | Strahler (1952) | Distribution shape. **Not** age or erosion rate |

## Geomorphic shape

| Family | Outputs (unit) | Definition and window | Citation | Claim boundary |
|---|---|---|---|---|
| Profile / plan / mean curvature | `{profile,plan,mean}_curvature.{…}` (1/m) | Zevenbergen–Thorne local quadratic fit over a 3×3 node neighbourhood; exactly 0 on any tilted plane; on `z=a(x²+y²)` returns −2a, +2a, −4a | Zevenbergen & Thorne (1987) | Lumps, hollows, ridges, channels. **Not** sediment or flow process |
| Vector Ruggedness Measure | `vector_ruggedness.{…}` (0–1) | One minus the resultant length of unit surface normals in the window; 0 on any plane however steep, rising with orientation disorder | Sappington et al. (2007) | Orientation dispersion only, decoupled from mean slope |
| Surface-area ratio (rugosity) | `surface_area_ratio.{…}` (≥1) | True surface area over planar area; exactly 1 on flat ground, `sec(slope)` on a tilted plane | — | Geometry only |
| Terrain Ruggedness Index | `terrain_ruggedness_index.{…}` (metres) | Mean absolute elevation difference from the centre cell in the window | Riley et al. (1999) | Local roughness |
| Structure function + Hurst | `structure_function.<lag>` (metres), `hurst_exponent` (0–1) | RMS elevation difference at each lag, pooled over axes; log-log slope estimates H; exactly 1 on a linear ramp, ~0 on white noise | Mandelbrot & Van Ness (1968); Turcotte (1997) | Scale-aware roughness. **Not** a fractal claim about the terrain |
| Wood curvature classes | `curvature_classes.composition.{planar,peak,pit,ridge,channel,pass}`, `dominant_class` (fraction) | Sign of principal curvatures at each cell, classified into the six Wood forms | Wood (1996); Dikau (1989) | Descriptive form labels |
| Woodcock fabric | `fabric_eigen.{eig1,eig2,eig3,woodcock_K,woodcock_C,isotropy}` (dimensionless) | Eigen-analysis of the surface-normal orientation tensor; `C` separates clustered from girdled fabrics | Woodcock (1977) | Fabric shape, not a geologic fabric |

## Landform and line of sight

| Family | Outputs (unit) | Definition and window | Citation | Claim boundary |
|---|---|---|---|---|
| Topographic openness | `openness.{positive,negative}_{median,p10,p90}` (degrees) | Mean zenith / nadir sight-line angle over eight azimuths to a fixed radius; exactly 90° on a plane, >90° at a summit | Yokoyama, Shirasawa & Pike (2002) | Exposure / enclosure at map scale |
| Openness-difference slope position | `openness_difference.{slopepos_*,ridge_fraction,valley_fraction,midslope_fraction}` (degrees, fraction) | Positive minus negative openness, classified into ridge / midslope / valley | Yokoyama (2002) | Slope position, not stability |
| Geomorphons | `geomorphons.composition.<10 forms>`, `spectrum`, `dominant_form` (fraction) | Eight-direction line-of-sight ternary signature reduced to ten named forms; the reduction is an explicit antisymmetric rule validated against canonical shapes, **not** a verbatim GIS lookup | Jasiewicz & Stepinski (2013) | Descriptive landform composition |
| Weiss TPI classes | `tpi_landform.composition.<6 classes>`, `dominant_class` (fraction) | Topographic Position Index over one window, classified to ridge/upper/middle/lower/valley/flat | Weiss (2001) | Slope position |
| Two-scale TPI | `multiscale_tpi.composition.<7 classes>`, `dominant_class` (fraction) | TPI evaluated at two nested windows and combined, so a cell that is a hilltop at both scales is distinguishable from one that is not | Weiss (2001) | Nested position |
| Sky-view factor | `svf.{mean,median,p10,p90,min}` (0–1) | Hemispherical openness from the horizon angles; exactly 1 on a flat surface | Zakšek, Oštir & Kokalj (2011) | Illumination geometry as context. **Not** power or imaging performance |
| Melton relief | `melton_relief.{total_relief_m,melton_ruggedness,relief_ratio,elevation_relief_ratio}` (m, dimensionless) | Basin relief over √area and the elevation–relief ratio; the latter cross-checks the hypsometric integral | Melton (1965); Pike & Wilson (1971) | Relief scalars |

## Scale and fabric

| Family | Outputs (unit) | Definition and window | Citation | Claim boundary |
|---|---|---|---|---|
| Radial power spectrum | `spectral.{spectral_slope,total_power,roughness_rms,peak_wavelength_m,rough_long,rough_mid,rough_short}` (dimensionless, m², m) | Detrend, Hann-window, 2-D FFT, radially average the periodogram over `k_r`; total power recovers the detrended variance by Parseval | Perron, Kirchner & Dietrich (2008) | How roughness is shared across wavelengths |
| Directional structure function | `anisotropy.{strength,orientation_deg,isotropy,mean_roughness}` (0–1, degrees, m) | RMS elevation difference along a fan of azimuths; orientation is the azimuth of *minimum* roughness (the strike of ridges or dunes) | Shepard et al. (2001) | Fabric strength and orientation |
| Haar wavelet spectrum | `wavelet.energy_by_level.<1–6>`, `dominant_level`, `total_detail_energy`, `detail_loglog_slope` (m², dimensionless) | Orthonormal 2-D Haar multiscale detail energy; a period-2 checkerboard puts all energy at level 1 | Mallat (1989) | Multiscale energy partition |
| Kreslavsky–Head baseline roughness | `kh_roughness.{baseline_roughness_fine,coarse,profile.<lag>,profile_loglog_slope}` (degrees) | Differential slope (second difference) over declared baselines at 0.6–2.4× the effective resolution — the metric behind NASA’s global MOLA roughness maps | Kreslavsky & Head (2000) | Baseline roughness as published |
| RMS / Allan roughness length | `roughness_length.{rms_height,rms_slope,hurst_deviogram,roughness_length_m}` (m, dimensionless) | Deviogram of elevation differences; the lag at which RMS deviation reaches `rms_height` is the roughness length | Shepard et al. (2001) | Scale-aware roughness length |
| Semivariogram | `variogram.{sill,nugget,range_m,vario_loglog_slope,aniso_ratio}` (m², m) | Matheron estimator over lag bins; range = distance at which the sill is reached | Matheron (1963) | Spatial structure. **Not** a predictive geostatistical model |
| Surface-normal roughness | `normal_roughness.{roughness_mean,roughness_median,roughness_p90}` (dimensionless) | Dispersion of unit surface normals; ≈ 0 on any plane | Hobson (1972); McKean & Roering (2004) | Orientation disorder |

## Flow geometry, texture, and position

| Family | Outputs (unit) | Definition and window | Citation | Claim boundary |
|---|---|---|---|---|
| D8 flow dissection | `drainage.{channel_fraction,mean_log_acc,max_acc_fraction,drainage_density_proxy}` (fraction, log) | Priority-flood depression fill, then D8 accumulation; mass is conserved (outlet accumulations sum to the finite cell count) | O’Callaghan & Mark (1984); Barnes et al. (2014) | Purely geometric routing texture. **Not** hydrology |
| Topographic Wetness Index | `twi.{mean,median,p10,p90,std}` (dimensionless) | `ln(a / tan β)`; greater on gentler ground at equal contributing area | Beven & Kirkby (1979) | Convergence proxy |
| Convergence index | `convergence.{mean,median,std,convergent_fraction,divergent_fraction}` (degrees) | Mean aspect deviation within the window with the sign of terrain divergence | Köthe & Lehmeier (1996); Kiss (2004) | Flow convergence |
| Slope–area concavity | `slope_area.{flint_theta,r2,log_ks,n_bins_used}` (dimensionless) | Log-log regression of slope against contributing area; a concave surface gives θ > 0 | Flint (1974) | Concavity index |
| Fractal dimension | `fractal.{box_count_dimension,r2,n_scales}` (dimensionless) | Differential box-counting dimension; ≈ 2 on a plane | Sarkar & Chaudhuri (1994) | Space-filling complexity |
| Lacunarity | `lacunarity.{lacunarity_mean,lacunarity_r2,lacunarity_loglog_slope}` (dimensionless) | Gliding-box mass variance; exactly 1 for a uniform field | Plotnick, Gardner & O’Neill (1993) | Gap texture |
| Shannon entropy | `entropy.{slope_entropy,elevation_entropy,slope_entropy_norm,elevation_entropy_norm}` (dimensionless) | Histogram entropy of slope and elevation; 0 on a constant field | Shannon (1948) | Complexity index |
| Hypsometric curve | `hypsometry.{integral,skew,kurtosis,curve}` (dimensionless) | Strahler area–altitude curve plus its shape moments | Strahler (1952) | Distribution shape |
| Iwahashi–Pike terrain class | `iwahashi_pike.{slope_mean,convexity_mean,texture_mean,composition.<0–7>,dominant_class}` (degrees, dimensionless, fraction) | Three-signature (slope / convexity / texture) unsupervised nested-means classification | Iwahashi & Pike (2007) | Descriptive class. **Not** geology |
| TPI dispersion | `tpi_dispersion` (metres) | Spread of the Topographic Position Index over the tile | Weiss (2001) | Positional variability |

## Windows, thresholds, and excluded scales

`descriptor_bank(z, dx=…, window=5)` fixes the moving window in **pixels**; every physical window in
a study is therefore `window × dx` metres at the declared support, and the study config declares both
`target_support_m` and (for the benchmark) `extent_m`. The comparability gate
(`comparability.py`) refuses any cell whose units are not genuinely matched and whose support is below
every unit’s effective resolution, so **a feature is never displayed at a scale the data cannot
support** — that is the release target “no display uses a value below its supported scale”.

Excluded from every decision, by construction: rock-scale obstacles below the pixel, composition,
vegetation type, trafficability, and every physical process in the transfer-gap ledger.
