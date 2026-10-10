# Real-data runbook

Run these steps on a machine with internet access. The TerraTrace sandbox has no
outbound network, so downloads happen on your computer.

## 1. Install real-data extras

```bash
pip install -r requirements-real.txt    # rasterio, requests, PyYAML
```

## 2. Get the one required key

Create a free OpenTopography account and copy an API key:
`https://portal.opentopography.org` → My Account → API key.

```bash
export OPENTOPO_API_KEY=your_key_here
```

No key is needed for Mars MOLA.

## 3. Get the Mars reference DEM (no key)

Download the **Mars MGS MOLA DEM 463m** GeoTIFF from USGS Astrogeology:
`https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m`

Save it as `data/mars/mola_463m.tif`. (Primary archive, for citation and the native
MEGDR products: `https://pds-geosciences.wustl.edu/missions/mgs/megdr.html`.)

Pick a bounded Mars analysis window (a sub-region), not the whole globe, for a
map-scale study.

## 4. Preflight the AOI config (no network)

Before downloading anything, dry-run the config. Preflight validates every bounding
box, picks the catalog source that actually covers each AOI, and prints an approximate
request size so a malformed or oversized AOI is caught before a byte moves:

```bash
python3 scripts/fetch_real_dems.py --config config/aois.example.yml --preflight-only
```

Hard problems (e.g. `west >= east`, latitude out of range, no covering source) make it
exit non-zero. Size-limit breaches are warnings, not errors.

## 5. Fetch the Earth candidate DEMs

```bash
python3 scripts/fetch_real_dems.py --config config/aois.example.yml
```

Preflight runs again automatically and aborts on hard problems (pass `--skip-preflight`
to override). For each Earth unit it calls the OpenTopography `globaldem` API
(`demtype=COP30` by default) and writes GeoTIFFs into `data/earth/`. To pull a
higher-resolution US product instead, set `dataset: USGS10m` (or `USGS30m`) on that unit
— the fetcher dispatches to the 3DEP `usgsdem` API with the same key. Downloads are
atomic (`.part` → rename) and retry transient 429/5xx responses with backoff. After each
file lands it is given a quick QA profile (valid / water / NaN fraction, relief, flags).

## 6. QA a downloaded DEM (optional)

```bash
python3 scripts/profile_dem.py data/earth/candidate_b_cop30.tif
python3 scripts/profile_dem.py --bbox -115.8 36.0 -115.4 36.4 data/earth/candidate_a_cop30.tif
```

Reports valid/water/NaN fractions, robust relief (p99−p1), percentiles, and advisory
flags. It exits non-zero on a blocking flag (`ALL_NAN` / `LOW_VALID_FRACTION` /
`WATER_CONTAMINATION`) — the water flag is the same `zero_fraction > 0.6` gate the engine
uses, so a mostly-ocean AOI (a classic contamination trap) is caught early.

## 7. Run the real study

```bash
PYTHONPATH=. python3 scripts/run_real_study.py --config config/aois.example.yml
```

It writes `artifacts/study.json` (+ manifest/checksums) and `viewer/index.html`. With
≥2 eligible Earth candidates the package also carries a Pareto **frontier** ranking.

## Data terms and citation (required)

| Source | Terms | Cite as |
|---|---|---|
| Mars MOLA MEGDR / USGS DEM | NASA PDS / USGS public; attribution required | Smith et al., MGS MOLA MEGDR; USGS Astrogeology |
| Copernicus GLO-30 | ESA Copernicus; attribution required | © ESA Copernicus DEM, via OpenTopography |
| USGS 3DEP (optional) | US public domain | USGS 3D Elevation Program |

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
  convention (0–360 east vs −180–180), or set `reproject: false` to use the
  simpler same-dx fallback while you investigate.
- Treat Mars 463 m as the limiting support: do not claim sub-support structure.
- Keep the transfer-gap ledger visible; morphology similarity is not transfer validity.
- Mark any unit with unverified access/rights/ecology status as ineligible.
