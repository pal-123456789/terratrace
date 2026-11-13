# First real lunar terrain in TerraTrace (exploratory)

**Status: EXPLORATORY. Not a confirmatory result, and not a claim about any lunar base site.**

TerraTrace now ingests and analyses **real lunar elevation data**. This page records exactly what
was run, what it found, and what it does not establish. The confirmatory Mars benchmark (protocol
v3) is untouched.

## 1. The data

| | |
|---|---|
| Product | NASA Goddard PGDA, *South Pole Landing Site LOLA DEMs*, **Site01 — Connecting ridge** |
| File | `Site01_final_adj_5mpp_surf.tif` |
| sha256 | `3ba7b97cb00a2bcf21189c3aeb535f65afc21207154ab9f0d43c5bdc1f7e747e` |
| Grid | 3200 x 3200 at **5.0 m/pixel** = **16.0 km x 16.0 km** |
| CRS | south polar stereographic, metres, MOON_ME frame of DE421 (R = 1 737 400 m) |
| Elevation | -523.2 to 1959.5 m; no nodata |
| Citation | Barker et al. (2021), *Planet. Space Sci.* **203**, 105119; site numbering from Mazarico et al. (2011), *Icarus* **211**, 1066-1081 |

The archive publishes six south-polar candidate regions, each with an elevation raster, a slope
raster, a **total elevation-uncertainty raster** and a LOLA observation-count raster. **Only the
elevation raster for Site01 was downloaded here.** The uncertainty and count rasters were not
retrieved, so nothing in this page propagates measurement uncertainty — see §5.

These are **published lunar south-polar candidate regions used as topographic reference areas**.
They are not officially approved base locations, and nothing here claims they are.

## 2. Why the regime differs from the Mars panel

The published product is 16 km across. The Mars benchmark uses a **60 km** extent. A 60 km window
cannot be cut from a 16 km tile, so this is a **separate, declared regime** rather than a forced
common one:

| | lunar / Earth here | Mars panel (v3) |
|---|---|---|
| extent | 16 km | 60 km |
| supports | 500 / 750 / 1000 m | 1500 / 2000 / 3000 m |
| cells per side | 32 / 21 / 16 | 40 / 30 / 20 |

**Mars is deliberately excluded.** MOLA's effective floor is 1389 m, above every support tested
here, so a Mars unit would be compared below the scale its source can carry. The comparability gate
would have refused it; rather than disable the gate, Mars is left out and said so.

Both bodies here are comfortably in regime: the lunar source (5 m) has a 3x floor of 15 m and the
Earth source (30 m) of 90 m, well below 500 m.

## 3. The declared axes

This is **not** the frozen core-lens axis set, and it is not presented as one. Three axes, each
computed by the engine's own descriptor functions, and each named in the output:

1. **mean slope**, degrees — `features.slope_deg`
2. **mean 3x3 local relief**, metres — `features.relief`
3. **window elevation standard deviation**, metres — the roughness family the v3 sigma labels report

The decision is the engine's Pareto machinery (`decision.non_dominated`), over **distances to the
reference**, each expressed as a fraction of the reference's own value so the three axes are
commensurate without inventing a weighting. There is no composite score.

## 4. What was found

Reference, Site01: **mean slope 10.3-11.2 deg, relief 249-452 m, elevation std 411-421 m** across
the three supports. The lunar south-polar site is **rough terrain**, not a smooth plain.

Distances to the reference as a fraction of the reference value, and Pareto layer-1 membership:

| Earth candidate | support 500 m | 750 m | 1000 m |
|---|---|---|---|
| **Nevada Basin & Range** | 0.001 / 0.102 / 0.132 **L1** | 0.072 / 0.000 / 0.116 **L1** | 0.136 / 0.076 / 0.136 **L1** |
| Odadahraun (Iceland) | 0.637 / 0.658 / 0.667 | 0.624 / 0.705 / 0.666 | 0.627 / 0.748 / 0.679 |
| Harrat Khaybar | 0.835 / 0.815 / 0.835 | 0.850 / 0.835 / 0.832 | 0.861 / 0.850 / 0.836 |
| Deccan Traps | 0.897 / 0.888 / 0.940 | 0.912 / 0.906 / 0.940 | 0.922 / 0.916 / 0.942 |
| Snake River Plain | 0.957 / 0.955 / 0.940 | 0.958 / 0.959 / 0.939 | 0.959 / 0.960 / 0.940 |
| Llano Estacado | 0.979 / 0.977 / 0.980 | 0.981 / 0.980 / 0.980 | 0.983 / 0.982 / 0.980 |
| Nullarbor Plain | 0.988 / 0.987 / 0.992 | 0.991 / 0.990 / 0.992 | 0.992 / 0.992 / 0.992 |

(d_slope / d_relief / d_std. L1 = Pareto layer 1.)

**One Earth candidate is non-dominated at every support: the Nevada Basin & Range**, matching the
lunar site's relief to within 0.000-0.102 of the reference value and its slope to within
0.001-0.136. Every other candidate is dominated by it on all three axes.

**This is the interesting part, and it is a different answer from the Mars panel.** For Martian
volcanic plains the non-dominated candidates were the *smooth* non-volcanic controls — Nullarbor
and Llano Estacado — and the roughest candidate was irrelevant. For a real lunar south-polar site
those same two are the **worst** matches on every axis, and the terrain that answers is a
basin-and-range extensional landscape, which is nothing like a volcanic plain.

Different reference, different analog — which is the project's whole argument against a single
"planetary similarity" score.

## 5. What this does NOT establish

It does not establish that the Nevada Basin & Range is a useful lunar analog in any operational
sense. In particular:

- **No uncertainty propagation.** The published elevation-uncertainty rasters exist and were not
  retrieved. The "distance fraction" is therefore nominal, with no error bar, and no perturbation
  test of whether layer-1 membership survives realistic noise. *This is the single largest gap.*
- **One lunar site.** Site01 only; five other published regions were not analysed.
- **Three declared axes**, not the frozen core-lens set, and not the full descriptor bank.
- **Relative distances, no adequacy test.** Being nearest among seven candidates is not the same as
  being adequate; no absolute-adequacy threshold was applied (the Mars panel has one).
- **No adversarial stress test** (crop origin, control removal) on this panel.
- **Earth candidates are Copernicus GLO-30 surface models**, which can include vegetation and
  buildings, while the lunar product is bare rock. That is a real transfer gap, not a detail.
- **No claim about base suitability, illumination, thermal environment, regolith mechanics,
  communications or access.** Morphology only. Sixteen kilometres of a connecting ridge says
  nothing about whether anything should be built there.
- No external reviewer has examined this.

## 6. Reproduce it

```bash
# 1. fetch the product (41 MB; resumable chunked downloader for slow links)
python scripts/fetch_lola.py "Site01/Site01_final_adj_5mpp_surf.tif" data/moon/Site01_surf.tif
# 2. run the comparison
python scripts/lunar_site01_demo.py
```

Writes `artifacts/lunar_site01/lunar_site01_exploratory.json` and `docs/figures/lunar-site01.png`.
Verify the input with
`sha256sum data/moon/Site01_surf.tif` against the value in §1.

## 7. Status

| item | status |
|---|---|
| Real lunar terrain ingested | **IMPLEMENTED AND TESTED** |
| Exploratory lunar comparison | **IMPLEMENTED AND TESTED** |
| Uncertainty propagation | **NOT STARTED** — the published uncertainty rasters were not retrieved |
| Confirmatory lunar protocol | **NOT STARTED** — a frozen v4 would be needed |
| Lunar base suitability, of any kind | **NOT CLAIMED** |
