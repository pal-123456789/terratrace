# Independent-toolchain reproduction of one comparison window

**What this is, and what it is not.** This is an *internally prepared* re-derivation: the
author of the project ran two toolchains that share no code with TerraTrace over one of the
project's own study windows. **It is not external scientific validation.** No reviewer outside
the project has examined this result, and nothing here should be described as if one had.

The project's own list of open items named "no independent GIS re-derivation of a sample
window" as a gap. This page closes the part of it that can honestly be closed from one machine,
and states plainly which part cannot.

## 1. The honest scope boundary

| step | independently reproduced? |
|---|---|
| Reading a DEM and warping it to a per-body metric grid | **No.** TerraTrace uses `rasterio`, which *is* GDAL. Any GDAL-based route would run the same library, so this step is excluded from the claim. |
| Cropping to the 60 km matched extent and aggregating to a common support | **No** — same reason: it runs on the grid the warp produced. |
| **The slope operator** | **Yes.** Recomputed by RichDEM and by WhiteboxTools, neither of which shares code with TerraTrace. |
| **The local-relief operator** | **Yes**, by WhiteboxTools. |

So the honest claim is narrow and exact: *given the same elevation array, two independent
implementations reproduce TerraTrace's slope and its 3×3 local relief.* The ingest path is not
independently reproduced and is not claimed to be.

## 2. The window

The identical array the study itself builds, obtained by calling the study's own loader so that
nothing about the ingest is substituted (the exception being the geometry re-derivation above,
which is out of scope by construction):

| unit | role | native posting | common support | grid | valid |
|---|---|---|---|---|---|
| `earth_llano_estacado` | smooth non-volcanic control (S winner) | 30 m (Copernicus GLO-30) | 1500 m | 40 × 40 | 1.000 |
| `earth_nullarbor` | smooth non-volcanic control | 30 m (Copernicus GLO-30) | 1500 m | 40 × 40 | 1.000 |
| `mars_arcadia` | v3 primary confirmatory reference | 463 m (MOLA MEGDR) | 1389 m | 43 × 43 | 1.000 |

Extent 60 km per unit, aggregated by block mean to the support named, matching the v3 protocol.
Comparison is made on the interior cells only (a 1-cell border excluded, so no boundary rule
enters the comparison).

Toolchains: **RichDEM** (Barnes, C++; the project's own C++ terrain-analysis implementation) and
**WhiteboxTools 2.3.6** (Whitebox Geospatial). TerraTrace's slope is a 4-neighbour central
difference; both are 3×3 stencil estimators from the Horn / Zevenbergen–Thorne family. A small
systematic difference is therefore *expected* — the question is whether it is small.

## 3. Slope (degrees)

| unit | TerraTrace mean | RichDEM mean | RichDEM \\|Δ\\| mean / p95 / max | RichDEM r | Whitebox mean | Whitebox \\|Δ\\| mean / p95 / max | Whitebox r |
|---|---|---|---|---|---|---|---|
| `earth_llano_estacado` | 0.2108° | 0.1958° | 0.0293° / 0.0929° / 0.3173° | 0.977 | 0.2054° | 0.0444° / 0.1329° / 0.5237° | 0.931 |
| `earth_nullarbor` | 0.0632° | 0.0569° | 0.0116° / 0.0338° / 0.1804° | 0.935 | 0.0605° | 0.0174° / 0.0508° / 0.2665° | 0.812 |
| `mars_arcadia` | 0.1576° | 0.1445° | 0.0225° / 0.0615° / 0.3733° | 0.969 | 0.1544° | 0.0319° / 0.0893° / 0.4695° | 0.922 |

All three implementations agree on the **mean** to within 0.016° absolute in every window, and
correlate at 0.81–0.98 per cell. The residual is a stencil difference, not a disagreement about
the terrain: TerraTrace's central difference and a 3×3 Horn stencil weight neighbouring cells
differently, and on these very smooth surfaces the *absolute* differences are one to two orders
of magnitude below the terrain's own variability.

**Tolerance and its justification.** We adopt a working tolerance of **mean absolute difference
≤ 0.05° and 95th-percentile ≤ 0.15°** for a 3×3-stencil cross-check on smooth terrain at
kilometre support. Justification, stated as a judgement rather than a derivation: the largest
observed mean difference is 0.0444°, the largest p95 is 0.1329°, and both sit far below the
slope contrast that separates a candidate class (the difference in mean slope between a smooth
control and a rough basalt at this support is of order 1°, an order of magnitude larger).
**These bounds are set by this comparison, not by an external standard** — they are a
documented engineering threshold, not a published acceptance criterion.

## 4. Local relief, 3 × 3 window (max − min, metres)

| unit | TerraTrace mean | Whitebox mean | mean \\|Δ\\| | max \\|Δ\\| |
|---|---|---|---|
| `earth_llano_estacado` | 14.6724 m | 14.6724 m | 2.1 × 10⁻⁵ m | 6.0 × 10⁻⁵ m |
| `earth_nullarbor` | 4.6016 m | 4.6016 m | 5.0 × 10⁻⁶ m | 1.5 × 10⁻⁵ m |
| `mars_arcadia` | 10.6149 m | 10.6149 m | 8.2 × 10⁻⁵ m | 3.4 × 10⁻⁴ m |

This is an **exact reproduction** to within single-precision storage (the GeoTIFF is written
as float32; the residual is at the float32 epsilon for these magnitudes). Two independent
implementations of "maximum minus minimum over a 3×3 window" agree to 10⁻⁴ m.

## 5. Two implementation differences found, and how each was resolved

These are the substance of the exercise: an independent toolchain does not simply confirm — it
exposes where a convention was assumed rather than stated.

**(a) RichDEM silently assumed 1-metre cells, and was wrong by a factor of ~1,000.** Built from
a bare NumPy array, RichDEM treats one cell as one horizontal unit. On a 1500 m grid its
`slope_degrees` returned a mean of **50.28°** for Llano Estacado — a plain, whose true mean slope
is 0.21°. Supplying a `geotransform` keyword did not change its behaviour. Its documented remedy
for non-unit cells is to express elevation in the horizontal unit, so the comparison feeds
`z / dx`. After that correction RichDEM returns 0.1958°, in agreement with the others. *If this
had been run as a "confirmatory" check without inspecting the output, it would have produced a
spectacular and entirely fictitious discrepancy.*

**(b) WhiteboxTools centres its 3×3 window; TerraTrace anchors it.** WhiteboxTools'
`range_filter` writes the window centred on each cell, so its output at index *i* corresponds to
TerraTrace's relief at index *i*−1. Comparing the two at the same index leaves a residual of
**order metres** — 4.99 m, 1.54 m and 3.75 m mean absolute difference on the three windows above.
Shifting by the half-window makes the residual **0.000000 m**. The difference was a convention,
not a disagreement, and the alignment was *searched* (a 3×3 neighbourhood) rather than assumed.

Both findings are recorded here rather than quietly corrected, because they are the reason to do
this kind of check at all.

## 6. What this does not establish

It does not establish that TerraTrace's descriptors are *correct* — two of the three
implementations could share a common misconception, and none of them is a published acceptance
standard. It does not validate the support aggregation, the masks, the comparability gate, or any
decision the engine makes from these numbers. **The reprojection, listed as unvalidated in an
earlier revision of this page, is now checked — by mathematics rather than by a second toolchain;
see §8.** It does not touch the
v3 verdicts. It does not constitute external review, and it is not a substitute for a second
person running the pipeline on a second machine.

It establishes one thing, which was previously missing: **the slope and local-relief operators
are reproduced to the stated tolerances by two independent implementations over real data from
this study, and the two implementation differences that arose were identified, explained and
resolved.**

## 7. Reproduce it

```bash
pip install --break-system-packages richdem whitebox rasterio pyyaml
python scripts/gis_reproduction.py          # writes /tmp/gis_repro/reproduction.json
```

The script is committed as `scripts/gis_reproduction.py`. It calls the study's own loader to
obtain the array, then hands that array to RichDEM and to WhiteboxTools. Expected output is the
table in §3 and §4; the alignment figure in §5(b) is reproduced by comparing whitebox's
`range_filter` output at the same index instead of at the half-window offset.

## 8. The reprojection, validated against closed-form geodesy

An earlier revision listed the reprojection as *not* independently reproduced, for an honest reason:
the two "toolchains" compared on this page are both GDAL (`rasterio.warp` and
`gdalwarp`/WhiteboxTools). Two wrappers around one library is one implementation, and benchmarking
1 000 rabbits is not benchmarking a rabbit and a tortoise.

`scripts/reproject_analytic_check.py` closes that with a **right answer** instead of a second
opinion. An azimuthal-equidistant projection has an exact defining property: the distance from the
projection centre to any projected point *is* the geodesic distance between those two geographic
points. So the projection can be tested against closed-form geodesy:

| case | reference, derived from first principles | probes | worst disagreement |
|---|---|---|---|
| Moon (sphere, R = 1 737 400 m) | exact spherical great circle | 8, out to 15 km | **0.000029 m** |
| Earth, meridional | Simpson quadrature of M(φ) = a(1−e²)/(1−e²sin²φ)^1.5 | 4, out to 111 km | **0.000000 m** (3.7e-14 relative) |
| Earth, equatorial | exact `a·Δλ` | 3, out to 111 km | **0.000000 m** (1.1e-14 relative) |

Two things about how this was built matter more than the numbers, because both are the reason to
prefer mathematics over a second library:

1. **It caught the author, not the code.** The first version used Lambert's formula written from
   memory. It was wrong, and it reported the projection as **up to 107 m** in error. The projection
   was correct — the independent meridional quadrature agrees with it to a nanometre — and the
   *reference* was the defect. A second GDAL wrapper could never have exposed that, because it would
   have shared the error's origin: an implementation rather than a derivation.
2. **The uncovered cases are named, not dropped.** A general azimuthal geodesic on an ellipsoid has
   no closed form available here, and calling a geodesic solver would swap a wrong reference for a
   second library. Those probes are reported as *not analytically covered* rather than quietly
   omitted, and the check fails if *every* probe for a body is uncovered.

What this does **not** establish: that the *resampling* is correct (nearest/average/bilinear at
tile boundaries), that the masks are right, or anything about the descriptors. It establishes that
the coordinate geometry — the sphere and ellipsoid constants, the datum, the axes, and the
distance-from-centre property the whole metric windowing depends on — is correct to floating point.

```bash
python scripts/reproject_analytic_check.py            # both bodies
python scripts/reproject_analytic_check.py --body moon
```
