# Lunar screening on real LOLA terrain (exploratory)

**Status: EXPLORATORY. Not a confirmatory result, and not a claim about any lunar base site.**

TerraTrace ingests and screens **real lunar elevation data** from all six published south-polar
candidate regions, and tests whether the answer survives the DEM's *own* published error. This page
records exactly what was run, what it found, and what it does not establish. The confirmatory Mars
benchmark (protocol v3) is untouched.

Supersedes the earlier single-site note; that run is still reproduced byte-for-byte as a self-check
(§4).

## 1. The data

NASA Goddard PGDA, *South Pole Landing Site LOLA DEMs* — 5 m/pixel GeoTIFFs, south polar
stereographic metres, MOON_ME frame of DE421 (R = 1 737 400 m). Site numbering follows Mazarico et
al. (2011); products and errors follow Barker et al. (2021).

| site | published name | extent | surf sha256 |
|---|---|---|---|
| Site01 | Connecting ridge | 16 km | `3ba7b97cb00a2bcf…` |
| Site04 | Shackleton rim | 16 km | `38ff70dbdf2f066c…` |
| Site07 | Peak near Shackleton | 16 km | `38aaee10bb4da4d6…` |
| Site11 | de Gerlache rim | 16 km | `58f3372c35bbd6ba…` |
| Site20 | Leibnitz beta plateau | 16 km | `e51451f3629ba7cd…` |
| Site23 | Malapert massif | 21 km | `12d280a59cd75804…` |

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

## 2. Why the regime differs from the Mars panel

Every site is ≈16 km across (Site23 is 21 km), so the Mars study's 60 km extent cannot be cut from
them. This is a **separate, declared regime**, not a forced common one:

| | lunar / Earth here | Mars panel (v3) |
|---|---|---|
| extent | 16 km (centre-cropped, so footprints stay equal) | 60 km |
| supports | 500 / 750 / 1000 m | 1500 / 2000 / 3000 m |
| cells per side | 32 / 21 / 16 | 40 / 30 / 20 |

**Mars is excluded by arithmetic, not convenience.** MOLA's effective floor is 1389 m — above every
support testable here — so a Mars unit would be compared below the scale its source can carry. The
comparability gate would refuse it; rather than disable the gate, Mars is left out and said so.

Both remaining bodies are comfortably in regime: the lunar source (5 m) has a 3x floor of 15 m and
the Earth source (30 m) of 90 m, well below 500 m.

## 3. The declared axes

Three axes, each computed by the engine's own descriptor functions and named in the output. This is
**not** the frozen core-lens set and is not presented as one:

1. **mean slope**, degrees — `features.slope_deg`
2. **mean 3x3 local relief**, metres — `features.relief`
3. **window elevation standard deviation**, metres

The decision is the engine's Pareto machinery (`decision.non_dominated`) over **distances to the
reference**, each expressed as a fraction of the reference's own value so the three axes are
commensurate without inventing a weighting. There is no composite score.

## 4. What was found

### Every site is rough terrain

Mean over the three supports; full per-support values are in the artifact.

| site | mean slope (deg) | mean 3x3 relief (m) | window std (m) |
|---|---|---|---|
| Site01 | 10.69 | 353.2 | 410.7 |
| Site04 | 19.53 | 738.0 | 1222.6 |
| Site07 | 9.56 | 329.0 | 438.6 |
| Site11 | 13.21 | 457.3 | 568.4 |
| Site20 | 11.25 | 391.5 | 626.5 |
| Site23 | 17.66 | 571.3 | 835.3 |

### One Earth candidate is non-dominated — at every site and every support

Distances to the reference as a fraction of the reference value (slope / relief / std), for the only
candidate that is ever non-dominated:

| site | 500 m | 750 m | 1000 m |
|---|---|---|---|
| **Site01** | 0.00 / 0.10 / 0.13 | 0.07 / 0.00 / 0.12 | 0.14 / 0.08 / 0.14 |
| **Site04** | 0.43 / 0.44 / 0.71 | 0.49 / 0.52 / 0.70 | 0.53 / 0.57 / 0.71 |
| **Site07** | 0.14 / 0.22 / 0.19 | 0.04 / 0.07 / 0.17 | 0.05 / 0.02 / 0.20 |
| **Site11** | 0.17 / 0.12 / 0.37 | 0.25 / 0.23 / 0.36 | 0.31 / 0.30 / 0.37 |
| **Site20** | 0.04 / 0.01 / 0.44 | 0.12 / 0.10 / 0.42 | 0.18 / 0.17 / 0.44 |
| **Site23** | 0.35 / 0.27 / 0.56 | 0.44 / 0.38 / 0.57 | 0.50 / 0.45 / 0.58 |

Across **18 of 18** site × support cells the sole non-dominated Earth candidate is
`earth_nevada_basin` (**Nevada Basin & Range**). The two smooth non-volcanic controls that answered
for Martian volcanic plains — Nullarbor and Llano Estacado — are the *worst* matches here, as they
were for the rougher lunar reference in the single-site run.

### ...but "non-dominated" is not "a good match"

The distances above are not uniformly small, and this is the most important thing on this page:

| site | worst-axis distance to the surviving candidate |
|---|---|
| Site01 (Connecting ridge) | 0.14 |
| Site07 (Peak near Shackleton) | 0.22 |
| Site11 (de Gerlache rim) | 0.37 |
| Site20 (Leibnitz beta plateau) | 0.44 |
| Site23 (Malapert massif) | 0.58 — no close candidate |
| Site04 (Shackleton rim) | 0.71 — no close candidate |

(Treating a worst-axis distance above 0.5 as "not close" is a **descriptive label, not a validated
adequacy criterion** — no adequacy threshold has been established in this regime, unlike the Mars
panel. The distances are reported so a reader can judge for themselves.)

For the two roughest sites — **Shackleton rim** and **Malapert massif** — the surviving candidate is
44-71% away on at least one axis. It is the *least-dissimilar member of a weak shortlist*, which is
precisely the failure mode this project identified and withdrew a claim over on the Mars side. So:
the screening is decisive about *ordering* everywhere, and decisive about *closeness* almost nowhere.

### The answer survives the DEM's own published error

LOLA's errors are spatially correlated, so the archive ships 100 *clones* per site: DEM realisations
drawn from the error covariance. Those are the correct input for a propagation test, and are used
here rather than independent per-pixel noise from the uncertainty raster. The reason is not pedantry:
adding independent Gaussian noise pixel-by-pixel and then aggregating to a 750 m block divides the
mean error by roughly √22500 = 150, which would manufacture a stability the data does not have.

| support | draws | exact-set match | distinct layer-1 sets | candidate frequency |
|---|---|---|---|---|
| 500m | 6 | 100% | 1 | Nevada in layer 1 for 100% |
| 750m | 6 | 100% | 1 | Nevada in layer 1 for 100% |
| 1000m | 6 | 100% | 1 | Nevada in layer 1 for 100% |

Six of the 100 published clones were retrieved, so this is a **6-draw ensemble, not a 100-draw one**,
and it covers **Site01 only**. It establishes that the layer-1 membership is not an artifact of
sampling noise at the scale of Site01's own error field; it does not establish stability at a
precision a 6-draw sample cannot resolve.

## 5. What this does NOT establish

- **Not adequacy.** Being nearest among seven candidates is not the same as being adequate. Two of
  six sites have no candidate within 50% on every axis (§4).
- **A narrow terrain class.** All six sites are south-polar highland/rim terrain. Their agreement may
  reflect that the six are geologically similar to each other rather than that the method is
  insensitive to the reference. Six nearby sites are not six independent tests.
- **A small ensemble, one site.** 6 of 100 clones, Site01 only.
- **Three declared axes**, not the frozen core-lens set, and not the full descriptor bank.
- **No adversarial stress test.** Crop origin, control removal and support jitter have not been run
  on this panel, unlike the Mars panel.
- **A real transfer gap.** Earth candidates are Copernicus GLO-30 *surface* models, which can include
  vegetation and buildings; the lunar product is bare rock.
- **No uncertainty on the Earth side.** Only the lunar DEM has a published error model; the Earth
  candidates are treated as exact.
- **No base suitability** of any kind — not illumination, thermal environment, regolith mechanics,
  communications or access. Morphology only. Sixteen kilometres of a connecting ridge says nothing
  about whether anything should be built there.
- **No external reviewer** has examined this.

## 6. Reproduce it

```bash
# elevation for all six sites (~41 MB each; the fetcher resumes, so re-run until complete)
python scripts/fetch_lola.py "Site01/Site01_final_adj_5mpp_surf.tif" data/moon/Site01_surf.tif
# ... likewise Site04, Site07, Site11, Site20, Site23
# Site01 only: its error realisations (the ensemble input)
python scripts/fetch_lola.py "Site01/Clones/Site01_final_adj_5mpp_0001_err.tif" data/moon/clones/Site01_0001.tif

# the analysis: six sites, three supports, plus the error ensemble
python scripts/lunar_sites_demo.py
```

Writes `artifacts/lunar_sites/lunar_sites_exploratory.json` and `docs/figures/lunar-sites.png`, and
**fails loudly** if the generalised code stops reproducing the published single-site result.

Verify an input against the provenance table above, e.g.
`sha256sum data/moon/Site01_surf.tif` → `3ba7b97cb00a2bcf21189c3aeb535f65afc21207154ab9f0d43c5bdc1f7e747e`.

## 7. Status

| item | status |
|---|---|
| Real lunar terrain ingested, six sites | **IMPLEMENTED AND TESTED** |
| Multi-site screening, 3 supports | **IMPLEMENTED AND TESTED** |
| Uncertainty propagation (author clones) | **IMPLEMENTED AND TESTED** — 6-draw ensemble, Site01 only |
| Full 100-clone ensemble, all six sites | **NOT STARTED** — 6 of 100 clones retrieved |
| Adversarial stress test on this panel | **NOT STARTED** |
| Confirmatory lunar protocol | **NOT STARTED** — would require a frozen v4 |
| Lunar base suitability, of any kind | **NOT CLAIMED** |
