# TerraTrace real-data runbook

Run these steps on a machine with internet access. The TerraTrace sandbox has no
outbound network, so every download happens on your computer.

The happy path is a single command: one orchestrator script takes a curated
multi-body config, validates it, fetches any missing Earth DEMs, runs the full
depth study (significance, bootstrap, landform, scale & fabric), writes a
self-contained bundle, and prints a one-line verdict. The manual three-step path
is still here as the advanced / step-by-step alternative (see the end).

## The one command

```bash
# Earth downloads need a free OpenTopography key (Mars MOLA is keyless):
export OPENTOPO_API_KEY=your_key_here

python3 scripts/run_real_analog_study.py --config config/real_multibody.example.yml
```

When it finishes, open the bundle's `report.html` (default output directory
`artifacts/real_study/`). In order, the orchestrator:

1. **Preflights** the config with zero network — validates every bounding box,
   picks the catalog source that actually covers each AOI, and prints the
   approximate download size.
2. **Fetches** any missing Earth DEMs. This is idempotent and cached: a DEM
   already on disk is reused, so re-runs don't re-download.
3. **Runs the study** on the real DEMs with the depth flags from the config on.
4. **Writes the bundle** and prints the headline (`result_state`,
   `recommended_unit`, the confidence verdict, and the significance of the
   recommendation vs the runner-up).

### Modes

| Flag | What it does |
|---|---|
| *(none)* | Real run: preflight -> fetch missing Earth DEMs (cached) -> study -> bundle. |
| `--dry-run` | No-network preflight only: validate bboxes, pick sources, print the approximate download size, then exit. Run this first. |
| `--synthetic` | Run the WHOLE pipeline on generated DEMs with no network and no rasterio, so you can see a full bundle before touching real data. |
| `--skip-fetch` | Skip the network fetch stage and go straight to preflight -> study -> bundle. Expects every DEM already on disk. |
| `--out DIR` | Bundle output directory (default `artifacts/real_study`). |

## 1. Prerequisites

### 1a. Install the real-data extras

```bash
pip install -r requirements-real.txt    # rasterio, requests, PyYAML
```

`--synthetic` and `--dry-run` do not need rasterio, requests, or a key — they run
on the base install (NumPy + PyYAML). The full real run needs all three.

### 1b. The OpenTopography key (env var only — the benchmark path does not need it)

The *multi-body analog orchestrator* on this page fetches its Earth candidates from OpenTopography,
which needs a free key. (The **matched-footprint benchmark** in §7 is **keyless**: it reads the public
ESA Copernicus GLO-30 COG mosaic straight from AWS Open Data — already verified bit-identical to the
OpenTopography product — so it needs no account and no key.)

Create a free OpenTopography account and copy an API key
(`https://portal.opentopography.org` -> My Account -> API key), then export it:

```bash
export OPENTOPO_API_KEY=your_key_here
```

Store the key **only** as an environment variable — never commit it to a file,
the config, or version control. It is needed only for the Earth downloads; the
Mars MOLA reference and the other planetary bodies are keyless.

### 1c. The Mars reference DEM (keyless)

Download the **Mars MGS MOLA DEM 463 m** GeoTIFF from USGS Astrogeology and save
it where the config expects it:

```bash
# https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m
# save as: data/mars/mola_463m.tif
```

The config crops this global file to a bounded Mars window by bbox — pick a
bounded analysis window, not the whole globe, for a map-scale study. (Primary
archive, for citation and the native MEGDR products:
`https://pds-geosciences.wustl.edu/missions/mgs/megdr.html`.)

## 2. Dry run first (zero network)

Validate the config and size the downloads before a single byte moves:

```bash
python3 scripts/run_real_analog_study.py \
    --config config/real_multibody.example.yml --dry-run
```

Preflight checks every bounding box (well-formedness, body bounds, coverage),
picks the catalog source that covers each AOI, and prints an approximate request
size. A malformed or uncovered AOI (`west >= east`, latitude out of range, no
covering source) exits non-zero so it is caught here, not mid-download.
Size-limit breaches are warnings, not errors.

## 3. See it work offline (synthetic)

Produce a full bundle from generated terrain — no network, no rasterio, no key —
so the output format is familiar before you touch real data:

```bash
python3 scripts/run_real_analog_study.py \
    --config config/real_multibody.example.yml --synthetic --out artifacts/synthetic_study
```

This runs the entire pipeline (study -> confidence -> bundle) on synthetic DEMs
with the same depth flags, and prints the same headline shape as a real run.

## 4. The real run

With the key exported and the Mars DEM in place:

```bash
export OPENTOPO_API_KEY=your_key_here
python3 scripts/run_real_analog_study.py --config config/real_multibody.example.yml
```

Read the printed headline, then open `artifacts/real_study/report.html`.

The headline reports the decision in one place (your values will differ):

```text
result_state     = RECOMMEND_FOLLOW_UP
recommended_unit = earth_candidate_b
confidence       = robust        # robust / qualified / fragile / tie / unverified
significance     = recommended vs runner-up significant (p < 0.05)
```

The bundle directory contains a complete, offline-openable deliverable:

- `study.json` — the full study package (features, distances, Pareto frontier,
  bootstrap, significance, landform, scale & fabric).
- `report.md` and `report.html` — the human-readable report.
- the offline interactive viewer.
- `REFERENCES` — data credits and method citations.
- `CHECKSUMS` — sha256 of every file in the bundle.
- `confidence.json` — the non-composite decision verdict and its signals.

## 5. Customise the config

`config/real_multibody.example.yml` is a curated starting point: a bounded Mars
reference window plus real Earth analog AOIs, with the depth flags turned on. To
study your own units, copy it and edit:

- **AOIs / bboxes** — each unit's `bbox: [west, south, east, north]` in degrees,
  and its `path`. Choose bounded, comparable terrain units, not whole named
  regions. Larger or alternate AOIs just change the config — no code edits.
- **Bodies** — the `reference` is Mars (keyless MOLA). Earth candidates fetch
  from OpenTopography; set `demtype` (`COP30`/`COP90`/`NASADEM`/`SRTMGL1`/
  `SRTMGL3`/`AW3D30`) or `dataset` (`USGS10m`/`USGS30m`) per unit. Other bodies
  (e.g. Moon LOLA) are keyless if you swap them in.
- **Depth flags** — the knobs that make this a deep study, already on in the
  example:

| Key | Example | Effect |
|---|---|---|
| `decision_metrics` | `extended` | Pareto axis set (`core`/`extended`/`geomorphic`/`landform`). |
| `n_boot` | `300` | Bootstrap resamples for distance CIs + non-domination frequency. |
| `significance` | `true` | Permutation test of the recommendation vs the runner-up. |
| `n_perm` | `1000` | Permutations for that test. |
| `landform` | `true` | Geomorphon landform composition + topographic openness. |
| `terrain_spectra` | `true` | Spectral slope / band roughness + directional fabric. |
| `previews` | `true` | Inline hillshade / landform preview PNGs in the report. |

On real DEMs prefer the block bootstrap for honest, autocorrelation-aware
intervals: set `bootstrap_method: block` (and `block_size` near the terrain's
correlation length). The default `independent` bootstrap is optimistically narrow
on real terrain. The config schema and per-unit keys match
`config/aois.example.yml` — see it for the fully commented field list.

## 6. Advanced / step-by-step (manual path)

The orchestrator wraps three scripts you can also run yourself when you want to
inspect each stage. These use `config/aois.example.yml` (core knobs) by default.

**1. Fetch the Earth DEMs** (preflight runs automatically):

```bash
python3 scripts/fetch_real_dems.py --config config/aois.example.yml --preflight-only  # validate only
python3 scripts/fetch_real_dems.py --config config/aois.example.yml                   # fetch
```

Fetching is idempotent (a file on disk is skipped; `--force` re-downloads),
records provenance in `data/fetch_manifest.json` (`--manifest` to override),
retries transient 429/5xx with backoff, and QA-profiles each file after it lands.
Pass `--skip-preflight` to override a hard preflight abort.

**2. QA a DEM (optional):**

```bash
python3 scripts/profile_dem.py data/earth/candidate_b_cop30.tif
```

Reports valid/water/NaN fractions, robust relief, and advisory flags; exits
non-zero on a blocking flag (`ALL_NAN` / `LOW_VALID_FRACTION` /
`WATER_CONTAMINATION`).

**3. Run the study, then bundle it:**

```bash
PYTHONPATH=. python3 scripts/run_real_study.py --config config/aois.example.yml
python3 scripts/export_bundle.py --study artifacts/study.json --out artifacts/bundle
```

`run_real_study.py` writes `artifacts/study.json` (+ manifest) and
`viewer/index.html`; `export_bundle.py` packages that study.json into the same
bundle layout (study.json, report.md, report.html, viewer, REFERENCES,
CHECKSUMS).

## 7. The keyless matched-footprint benchmark (protocol v3)

The panel benchmark whose result is written up in `docs/RESULTS-v3.md` reproduces in **two commands
with no API key and no account**: the Earth candidates come from the public ESA Copernicus GLO-30 COG
mosaic on AWS Open Data.

```bash
python3 scripts/fetch_earth_candidates.py --config config/matched_footprint_v3.yml --source cog
python3 scripts/run_matched_benchmark.py --config config/matched_footprint_v3.yml --out artifacts/mf_panel_v3
```

`--source cog` (the default) streams 1° GLO-30 tiles with HTTP range reads against the COG mosaic —
it never downloads the global mosaic and it needs no key. `--source opentopo` selects the older keyed
path instead. The Mars side is the same single global MOLA 463 m GeoTIFF (`data/mars/mola_463m.tif`);
both bodies need `rasterio`.

The run writes the panel JSON, a Markdown report, and the comparability-gate summary under
`artifacts/mf_panel_v3/`. The frozen decision rules are in `docs/BENCHMARK-PROTOCOL-v3.md`; the
result is in `docs/RESULTS-v3.md`.

## Data terms and citation (required)

| Source | Terms | Cite as |
|---|---|---|
| Mars MOLA MEGDR / USGS DEM | NASA PDS / USGS public; attribution required | Smith et al., MGS MOLA MEGDR; USGS Astrogeology |
| Copernicus GLO-30 / GLO-90 | ESA Copernicus; attribution required | (c) ESA Copernicus DEM, via OpenTopography |
| NASADEM | NASA/USGS public; attribution requested | NASADEM Merged DEM Global 1", via OpenTopography |
| SRTM GL1 / GL3 | NASA public; attribution requested | NASA SRTM GL1/GL3, via OpenTopography |
| ALOS AW3D30 | JAXA; attribution required | JAXA ALOS World 3D-30m, via OpenTopography |
| USGS 3DEP (10 m / 1 m) | US public domain | USGS 3D Elevation Program |

Each product's licence, citation, and vertical datum are also machine-readable in
`terratrace/catalog.py` (and copied into the fetch manifest + `sources.lock.yml`).
Do not redistribute source rasters if a provider prohibits it; distribute derived
artifacts and the retrieval recipe instead. Record exact product IDs, versions,
retrieval dates, and checksums in a `sources.lock.yml` for every published study.

## Scientific guardrails for real runs

- Choose bounded, comparable **terrain units**, not whole named regions.
- Reprojection is **on by default** (`reproject: true`): each AOI is warped to
  its own local azimuthal-equidistant metric grid at `target_support_m`, using
  the correct body (Mars sphere R=3,396,190 m; Earth WGS84). This is the correct
  way to compare morphology across bodies — do not disable it without reason.
- If the Mars warp returns an empty/BLOCKED unit, it is almost always a
  longitude-convention or CRS issue. Fixes: adjust the Mars `bbox` to the file's
  convention (0-360 east vs -180-180), or set `reproject: false` to use the
  simpler same-dx fallback while you investigate.
- Treat Mars 463 m as the limiting support: do not claim sub-support structure.
- When bootstrapping (`n_boot > 0`), prefer the **block** bootstrap on real DEMs
  (`bootstrap_method: block`) for honest, autocorrelation-aware confidence
  intervals; the default `independent` bootstrap is optimistically narrow.
- Keep the transfer-gap ledger visible; morphology similarity is not transfer
  validity.
- Mark any unit with unverified access/rights/ecology status as ineligible.

## Scope and claim firewall

TerraTrace does **map-scale terrain-morphology screening only**. A recommendation
means one Earth unit is morphologically closer to the Mars reference under the
chosen metrics — nothing more. It is **not** a claim about rover traversability,
hazard, geologic equivalence, site access, or mission readiness. The example AOIs
are illustrative analogs, not endorsements; verify access, rights, and ecological
status before any fieldwork. This project is independent research and is **not
NASA-endorsed**.
