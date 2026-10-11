# TerraTrace — a real five-world worked example

**Mars (MOLA) vs three real Earth analog terrains, at a common 1000 m support.**

> **Scope / claim firewall.** This is a map-scale terrain-**morphology** screen between
> curated map products. It is NOT a statement about rover traversability, autonomy,
> geological equivalence, site access, or mission readiness, and the Earth sites named
> here are **illustrative analogs**, not endorsed field sites. Not NASA-endorsed.

## The run

Produced by the one command, on real DEMs (downloaded on a networked machine):

```bash
py scripts/run_real_analog_study.py --config config/real_multibody.example.yml
```

- **Reference:** Mars, MGS **MOLA 463 m** DEM (USGS Astrogeology), a ~10°×10° equatorial window.
- **Candidates:** three real Earth terrains from **Copernicus GLO-30** (OpenTopography):
  - `earth_craters_of_the_moon` — Craters of the Moon basalt field, Idaho (a documented terrestrial basalt analog).
  - `earth_nevada_basin` — a Basin-and-Range desert window, Nevada.
  - `earth_andean_volcano` — Andean volcanic terrain, Ecuador.
- **Common support:** 1000 m (MOLA 463 m is the limiting resolution). **Decision lens:** extended (six axes).

## Result: an honest TIE (no forced winner)

```
result_state = TIE    recommended_unit = None
Pareto layer 1 (non-dominated): earth_craters_of_the_moon, earth_nevada_basin
Pareto layer 2:                 earth_andean_volcano   (dominated by Nevada)
```

Morphology distance to the Mars reference, per axis (lower = closer):

| candidate | slope | relief | ruggedness | connectivity | aspect disp. | hypsometric |
|---|---|---|---|---|---|---|
| Craters of the Moon | **0.75** | **0.78** | **0.76** | **0.018** | 0.39 | 0.28 |
| Nevada basin | 1.33 | 1.38 | 1.45 | 0.030 | **0.011** | **0.14** |
| Andean volcano | 1.73 | 1.50 | 1.85 | 0.057 | 0.012 | 0.17 |

<!-- APPEND_MARKER -->

Read it this way:

- On the **four core axes** (slope, relief, ruggedness, low-slope connectivity),
  **Craters of the Moon is far closer to Mars than any other candidate** — it dominates
  all four. On the core lens alone the engine therefore returns a single recommendation,
  **Craters of the Moon**, independently re-identifying a terrain that planetary scientists
  already use as a basalt analog.
- Adding the two **extended axes** flips the picture: **Nevada basin** matches Mars's
  directional-aspect dispersion and its hypsometric (elevation-distribution) structure far
  better. Neither candidate beats the other on all six axes, so they are Pareto-incomparable
  and the engine reports a **TIE** rather than inventing a winner.

That lens-dependence *is* the finding: the best analog depends on which morphology you
intend to test. TerraTrace surfaces it honestly instead of collapsing it into one score.
Run the full four-lens tie-break yourself (uses the cached DEMs, no re-download):

```bash
py scripts/run_real_analog_study.py --config config/real_multibody.example.yml --ablation --skip-fetch
```

## The terrains' real morphological fingerprints

Computed directly from the real DEMs (the opt-in landform / spectral / anisotropy blocks):

| unit | dominant landform | spectral slope β | anisotropy (strength @ orientation) |
|---|---|---|---|
| Mars (MOLA) | slope (with hollows, spurs) | −4.28 | 0.06 @ 45° |
| Craters of the Moon | **flat** (≈50%) | −3.15 | 0.10 @ 113° |
| Nevada basin | slope + hollow | −3.77 | 0.14 @ **45°** |
| Andean volcano | slope + spur | −4.07 | 0.14 @ 90° |

Note that **Nevada basin shares both Mars's dominant slope/hollow/spur landform mix and its
~45° fabric orientation** — consistent with its win on the extended axes — whereas Craters of
the Moon is morphologically a flatter basalt plain whose strength is the raw
roughness/relief/ruggedness match.

## An honest caveat (footprint mismatch)

The Mars window in this example config spans ~10°×10° (~590 km) while the Earth windows span
~0.4° (~40 km). At the common 1000 m support the per-pixel texture is comparable, but the Mars
sample covers a far larger footprint, so the comparison mixes regional Martian structure with
local Earth structure (visible as the ~279 km Mars spectral peak). This is exactly the kind of
transfer gap the ledger exists to flag. A cleaner run uses comparable-footprint AOIs: tighten
the Mars `bbox` in the config to a ~0.5° window over one specific unit (e.g. a lava plain in
Daedalia Planum) and re-run.

## Scale-resolved view (real)

Running the scale profile on the same data (`scripts/run_scale_profile.py`, core lens,
supports 1000–4000 m) shows the best analog is **not** scale-invariant. Overall core distance
to Mars per candidate (lower = closer):

| support (m) | best analog | Craters of the Moon | Nevada basin | Andean volcano |
|---|---|---|---|---|
| 1000 | Craters of the Moon | **1.32** | 2.41 | 2.95 |
| 1500 | — (tie) | **1.35** | 2.11 | 2.31 |
| 2000 | — (tie) | **1.35** | 2.11 | 2.31 |
| 3000 | Craters of the Moon | **1.33** | 2.09 | 2.12 |
| 4000 | Craters of the Moon | **1.32** | 2.33 | 2.01 |

Craters of the Moon is Pareto non-dominated at **every** scale (its analog scale-band spans the
whole 1000–4000 m sweep), reinforcing the atlas result. But the Andean volcano is non-dominated
only in the **1500–2000 m band**, where the candidates tie — its mid-scale (~1.5–2 km) texture is
where it most resembles this Mars window, and it steadily closes the gap as the support coarsens
(2.95 → 2.01). Quantifying the scale over which an analogy holds — and seeing it change — is
something a single-support comparison cannot do.

## Reproduce

See `REAL-DATA-RUNBOOK.md`. Everything is hash-anchored and offline-reproducible from the
fetched DEMs; the full bundle (study package, Markdown + HTML report, offline viewer,
references, checksums, and the decision-confidence summary) is written to `artifacts/real_study/`.
