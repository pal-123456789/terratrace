# Lunar screening on real LOLA terrain (exploratory)

**Status: EXPLORATORY. Not a confirmatory result, and not a claim about any lunar base site.**

TerraTrace ingests and screens **real lunar elevation data** from all six published south-polar
candidate regions, and tests whether the answer survives the DEM's *own* published error. This page
records exactly what was run, what it found, and what it does not establish. The confirmatory Mars
benchmark (protocol v3) is untouched.

**Read §2 first.** The first version of this screen shipped a defect — the two sides of every
comparison did not cover the same ground — and the numbers on this page are from the corrected
rerun. The defect is described with its measurements, because a page that quietly changed its
numbers would be worth less than one that says why.

## 1. The data

NASA Goddard PGDA, *South Pole Landing Site LOLA DEMs* — 5 m/pixel GeoTIFFs, south polar
stereographic metres, MOON_ME frame of DE421 (R = 1 737 400 m). Site numbering follows Mazarico et
al. (2011); products and errors follow Barker et al. (2021).

| site | published name | extent | surf sha256 |
|---|---|---|---|
| Site01 | Connecting ridge | 16 km | `3ba7b97cb00a2bcf...` |
| Site04 | Shackleton rim | 16 km | `38ff70dbdf2f066c...` |
| Site07 | Peak near Shackleton | 16 km | `38aaee10bb4da4d6...` |
| Site11 | de Gerlache rim | 16 km | `58f3372c35bbd6ba...` |
| Site20 | Leibnitz beta plateau | 16 km | `e51451f3629ba7cd...` |
| Site23 | Malapert massif | 21 km | `12d280a59cd75804...` |

| product | what it is |
|---|---|
| `SiteNN_final_adj_5mpp_surf.tif` | surface-interpolated elevation, metres |
| `SiteNN_final_adj_5mpp_toterr.tif` | total elevation uncertainty (RMS error), metres |
| `SiteNN_final_adj_5mpp_ldec.tif` | LOLA spot count per pixel |
| `SiteNN/Clones/SiteNN_final_adj_5mpp_NNNN_err.tif` | 100 perturbed DEM realisations per site |

**Retrieved for this run:** the elevation raster for all six sites; the uncertainty and count rasters
for Site01; and **six** of the 100 published clones for Site01. Nothing else was downloaded.

These are published lunar south-polar **candidate regions used as topographic reference areas**. They
are not approved base locations, and nothing here claims they are.

## 2. The defect in the first version, and the correction

The first screen (`artifacts/lunar_sites/lunar_sites_exploratory.json`, kept unchanged as the record
of what was actually computed) claimed "exact common support and matched footprint". Measured, it
did not have it:

| requested | Moon | Earth | equal? |
|---|---|---|---|
| 500 m | 500 m · 32 cells · **16.000 km** | 510 m · 31 cells · **15.810 km** | no |
| 750 m | 750 m · 21 cells · 15.750 km | 750 m · 21 cells · 15.750 km | yes, by luck |
| 1000 m | 1000 m · 16 cells · **16.000 km** | 990 m · 16 cells · **15.840 km** | no |

and the written record said `cells=[32, 32], support_m=500.0` for **both** sides. Two causes: each
body aggregated by its own integer factor (500/5 = 100 on the Moon, `round(500/30)` = 17 on Earth),
and `centre_square()` cropped to `min(n, h, w)` — silently turning a requested 32 × 32 Earth grid
into 31 × 31.

**This is the same failure class the project already withdrew a Mars claim over**: a comparison whose
footprints do not match, reported as though they did.

The correction (`terratrace/common_grid.py`, `scripts/lunar_sites_v2.py`, protocol in
[LUNAR-PROTOCOL-v2.md](LUNAR-PROTOCOL-v2.md)) warps **both bodies from their native source straight
into an exact destination grid** in the body's local azimuthal-equidistant CRS, with area-weighted
resampling. AEQD's defining property — the distance from the projection centre to any projected point
*is* the geodesic distance, validated analytically in
[INDEPENDENT-GIS-REPRODUCTION.md](INDEPENDENT-GIS-REPRODUCTION.md) — is what makes "500 m" mean
500 m of ground on both bodies. The lunar warp is not cosmetic: in the source polar stereographic
projection a nominal 500 m cell is up to **500.80 m of ground** at Site20.

The footprint is **9000 m**, not the obvious 15 km: because a local ground grid is *rotated* relative
to the LOLA tiles, its corners reach `half·√2` from the centre, and a 16 km tile admits at most
11.27 km. 9000 m is the largest value that fits every site and divides by all three supports, giving
**18 × 18, 12 × 12 and 9 × 9** cells at exactly 500, 750 and 1000 m — identical on both bodies, and
a comparison that is not on equal ground is refused by `common_grid.assert_comparable()` before it
can reach a ranking.

**What the correction changed.** The descriptors moved (Site01's mean slope at 750 m: 10.3° → 9.06°),
and — more importantly — so did the *closeness* numbers: Site20's worst-axis distance fell from 0.44
to 0.17 and Site23's from 0.58 to 0.36, because the window is now 9 km rather than 15.75 km. The
ordering conclusion did not move (see §4); the adequacy picture did, which is exactly the kind of
change a footprint mismatch would have been hiding.

## 3. Regime and declared axes

Every site is ≈16 km across (Site23 is 21 km), so the Mars study's 60 km extent cannot be cut from
them. This is a **separate, declared regime**, not a forced common one:

| | lunar / Earth here | Mars panel (v3) |
|---|---|---|
| footprint | 9000 m, exact, both bodies | 60 km |
| supports | 500 / 750 / 1000 m | 1500 / 2000 / 3000 m |
| cells per side | 18 / 12 / 9 | 40 / 30 / 20 |

**Mars is excluded by arithmetic, not convenience.** MOLA's effective floor is 1389 m — above every
support testable here — so a Mars unit would be compared below the scale its source can carry. The
comparability gate would refuse it; rather than disable the gate, Mars is left out and said so.
The lunar source (5 m) has a 3x floor of 15 m and the Earth source (30 m) of 90 m, both well below
500 m.

Three declared axes, each computed by the engine's own descriptor functions. This is **not** the
frozen core-lens set and is not presented as one: **mean slope** (degrees, `features.slope_deg`),
**mean 3×3 local relief** (metres, `features.relief`), and **window elevation standard deviation**
(metres). The decision is the engine's Pareto machinery (`decision.non_dominated`) over **distances
to the reference**, each expressed as a fraction of the reference's own value so the axes are
commensurate without inventing a weighting. There is no composite score.

## 4. What was found

### Every site is rough terrain

Mean over the three supports; per-support values are in the artifact.

| site | mean slope (deg) | mean 3×3 relief (m) | window std (m) |
|---|---|---|---|
| Site01 | 9.04 | 321.28 | 271.40 |
| Site04 | 23.35 | 830.77 | 1029.29 |
| Site07 | 9.81 | 334.72 | 272.99 |
| Site11 | 14.85 | 495.55 | 400.92 |
| Site20 | 10.67 | 315.93 | 260.38 |
| Site23 | 14.76 | 433.80 | 383.29 |

### One Earth candidate is non-dominated — at every site and every support

Distances to the reference as a fraction of the reference value (slope / relief / std), for the only
candidate that is ever non-dominated, `earth_nevada_basin` (**Nevada Basin & Range**):

| site | 500 m | 750 m | 1000 m |
|---|---|---|---|
| **Site01** | 0.20 / 0.21 / 0.12 | 0.12 / 0.10 / 0.12 | 0.09 / 0.00 / 0.12 |
| **Site04** | 0.52 / 0.53 / 0.70 | 0.56 / 0.58 / 0.70 | 0.59 / 0.61 / 0.71 |
| **Site07** | 0.12 / 0.16 / 0.12 | 0.04 / 0.05 / 0.12 | 0.02 / 0.04 / 0.11 |
| **Site11** | 0.25 / 0.23 / 0.24 | 0.32 / 0.30 / 0.24 | 0.36 / 0.35 / 0.24 |
| **Site20** | 0.02 / 0.15 / 0.17 | 0.05 / 0.10 / 0.17 | 0.09 / 0.06 / 0.17 |
| **Site23** | 0.24 / 0.14 / 0.20 | 0.31 / 0.19 / 0.21 | 0.36 / 0.24 / 0.21 |

Across **18 of 18** site × support cells the sole non-dominated Earth candidate is
`earth_nevada_basin`. The two smooth non-volcanic controls that answered for Martian volcanic plains
— Nullarbor and Llano Estacado — are the *worst* matches here, as they were for the rougher lunar
reference in the single-site run.

### The three axes are one axis, and this is the more important result

This is now derived, not merely measured. `slope_deg` is `degrees(arctan(|∇z|))` and
`relief(window=3, alpha=0)` is the 3×3 max-minus-min, so on a locally planar surface

    relief = 2 d · tan(slope) · ρ,    ρ = (|a| + |b|) / √(a² + b²) ∈ [1, √2]

with ρ depending **only on the gradient's direction**. The two descriptors are functions of the same
quantity, and their correlation is algebra rather than a discovery. Verified against the engine's own
functions on synthetic planes: worst error **4.4 × 10⁻¹⁶ m** in relief, **1.4 × 10⁻¹⁴ deg** in
slope, with observed ρ spanning exactly the provable **[1.0000, 1.4142]**.

On this panel the axes span **one dimension at every support** (effective rank 1; participation
ratio 1.001–1.036; Pearson up to +0.999, Spearman +1.000), the one-parameter planar fit recovers
**ρ = 1.25–1.28 — inside the provable band** — and **dropping any single axis leaves the
non-dominated set unchanged** at every site and support.

So "non-dominated on three axes at every support" is, on this panel, a **one-dimensional** statement:
the candidates are ordered along a single roughness/relief gradient and the survivor is the least
rough of the seven relative to each lunar reference. Three correlated roughness measures must not be
read as three independent dimensions of geological evidence — and the robustness reported below is
explained by that, because a one-dimensional ordering is far more stable than a genuine
three-dimensional Pareto front. Recorded in `artifacts/dependence/dependence_audit.json` and derived
in [LUNAR-PROTOCOL-v2.md](LUNAR-PROTOCOL-v2.md), not only here.

### ...but "non-dominated" is still not "a good match"

| site | worst-axis distance to the surviving candidate (500 / 750 / 1000 m) |
|---|---|
| Site01 (Connecting ridge) | 0.21 / 0.12 / 0.12 |
| Site07 (Peak near Shackleton) | 0.16 / 0.12 / 0.11 |
| Site20 (Leibnitz beta plateau) | 0.17 / 0.17 / 0.17 |
| Site23 (Malapert massif) | 0.24 / 0.31 / 0.36 |
| Site11 (de Gerlache rim) | 0.25 / 0.32 / 0.36 |
| Site04 (Shackleton rim) | **0.70 / 0.70 / 0.71** — no close candidate |

(Treating a worst-axis distance above 0.5 as "not close" is a **descriptive label, not a validated
adequacy criterion** — no adequacy threshold has been established in this regime, unlike the Mars
panel. The distances are reported so a reader can judge for themselves.)

For **Shackleton rim** the surviving candidate is **70-71% away on its worst axis at every support**.
It is the *least-dissimilar member of a weak shortlist*, which is precisely the failure mode this
project identified and withdrew a claim over on the Mars side. So the screening is decisive about
*ordering* everywhere, and decisive about *closeness* at five of six sites — and not at the sixth.
Absolute morphological adequacy has not been established.

### The answer survives the DEM's own published error

LOLA's errors are spatially correlated, so the archive ships 100 *clones* per site: DEM realisations
drawn from the error covariance. Those are the correct input for a propagation test, and are used
here rather than independent per-pixel noise from the uncertainty raster. The reason is not pedantry:
adding independent Gaussian noise pixel-by-pixel and then aggregating to a 750 m block divides the
mean error by roughly √22500 = 150, which would manufacture a stability the data does not have.

| support | realisations | exact-set match | distinct layer-1 sets | candidate membership |
|---|---|---|---|---|
| 500 m | 6 | 6 / 6 | 1 | Nevada in layer 1 for 6 / 6 |
| 750 m | 6 | 6 / 6 | 1 | Nevada in layer 1 for 6 / 6 |
| 1000 m | 6 | 6 / 6 | 1 | Nevada in layer 1 for 6 / 6 |

**Six sampled realisations out of the 100 available, for Site01 only.** Not a complete ensemble and
not a six-site uncertainty analysis. It establishes that the layer-1 membership is not an artifact of
sampling noise at the scale of Site01's own error field; it does not establish stability at a
precision a 6-realisation sample cannot resolve. The recorded counts, frequencies and set counts are
checked against each other by `terratrace/evidence.py`.

## 5. What this does NOT establish

- **Not adequacy.** Being nearest among seven candidates is not the same as being adequate, and at
  Shackleton rim no candidate is close at all (§4).
- **Three axes that are one axis.** The declared axes correlate at r ≈ 1.0, so the panel is a
  one-dimensional roughness screen dressed as a three-axis Pareto comparison (§4). This is the single
  most important limitation on this page.
- **A narrow terrain class.** All six sites are south-polar highland/rim terrain. Their agreement may
  reflect that the six are geologically similar to each other rather than that the method is
  insensitive to the reference. Six nearby sites are not six independent tests.
- **A small ensemble, one site.** 6 of 100 realisations, Site01 only.
- **A corrected exploratory reanalysis, not confirmation.** The same data was examined before this
  correction existed.
- **No adversarial stress test on this panel.** Crop origin, control removal, candidate-pool and
  support jitter have not been run here, unlike the Mars panel.
- **A real transfer gap.** Earth candidates are Copernicus GLO-30 *surface* models, which can include
  vegetation and buildings; the lunar product is bare rock.
- **No uncertainty on the Earth side.** Only the lunar DEM has a published error model; the Earth
  candidates are treated as exact.
- **No base suitability** of any kind — not illumination, thermal environment, regolith mechanics,
  communications or access. Morphology only. Nine kilometres of a connecting ridge says nothing about
  whether anything should be built there.
- **No external reviewer** has examined this.

## 6. Reproduce it

```bash
# elevation for all six sites (~41 MB each; the fetcher resumes, so re-run until complete)
python scripts/fetch_lola.py "Site01/Site01_final_adj_5mpp_surf.tif" data/moon/Site01_surf.tif
# ... likewise Site04, Site07, Site11, Site20, Site23
# Site01 only: its error realisations (the ensemble input)
python scripts/fetch_lola.py "Site01/Clones/Site01_final_adj_5mpp_0001_err.tif" data/moon/clones/Site01_0001.tif

# the corrected analysis: six sites, three supports, exact common grid, plus the error ensemble
python scripts/lunar_sites_v2.py

# and the toolchain that guards the grid itself
python tests/run_tests.py
```

Writes `artifacts/lunar_sites_v2/lunar_sites_v2.json`. It **self-checks** its own ensemble record
against `terratrace/evidence.py` and refuses to publish an inconsistent one.

Verify an input against the provenance table above, e.g.
`sha256sum data/moon/Site01_surf.tif` → `3ba7b97cb00a2bcf21189c3aeb535f65afc21207154ab9f0d43c5bdc1f7e747e`.

## 7. Status

| item | status |
|---|---|
| Real lunar terrain ingested, six sites | **IMPLEMENTED AND TESTED** |
| Exact common grid, both bodies, enforced | **IMPLEMENTED AND TESTED** (`common_grid`, 15 tests) |
| Corrected multi-site screening, 3 supports | **IMPLEMENTED AND TESTED** — 18/18 cells |
| Ensemble record internally checked | **IMPLEMENTED AND TESTED** (`evidence`, corruption-detected) |
| Axis-redundancy and leave-one-out analysis | **IMPLEMENTED** — result: one axis |
| Uncertainty propagation (author clones) | **IMPLEMENTED AND TESTED** — 6 of 100, Site01 only |
| Full 100-realisation ensemble, all six sites | **NOT STARTED** — 6 of 100 retrieved |
| Adversarial stress test on this panel | **NOT STARTED** |
| Confirmatory lunar protocol | **NOT STARTED** — would require held-out data and a pre-registered v3 |
| An axis that is not a roughness restatement | **NOT STARTED** — would need a real hypothesis first |
| Lunar base suitability, of any kind | **NOT CLAIMED** |
