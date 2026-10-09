# Data

Study inputs for TerraTrace. **Large raster DEMs are not all stored in git** — GitHub
rejects files over 100 MB, and the global Mars DEM is ~2 GB. This folder keeps the small,
redistributable inputs in the repo and documents how to regenerate the rest.

## What is in the repo

```
data/
  earth/   candidate_a_cop30.tif, candidate_b_cop30.tif   (Copernicus GLO-30 AOIs, a few MB)
  mars/    README.md  (+ mola_sample*.tif once you generate it)
```

## What is NOT in the repo (and why)

- `mars/mola_463m.tif` — the global **MGS MOLA 463 m** DEM, ~2 GB. It exceeds GitHub's
  100 MB per-file limit, so it is git-ignored. Download it once with the runbook, or crop
  a small committable sample (below).

## Regenerate / fetch

```bash
# Earth AOIs (needs a free OpenTopography key):
export OPENTOPO_API_KEY=...
python scripts/fetch_real_dems.py --config config/aois.example.yml

# Mars global DEM (no key): download "Mars MGS MOLA DEM 463m" GeoTIFF from USGS Astrogeology
#   https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m
# save as data/mars/mola_463m.tif

# Make a small, committable Mars AOI sample from the global file:
python scripts/make_mars_sample.py --config config/aois.example.yml
```

## Attribution / terms

- Mars: NASA PDS / MGS MOLA MEGDR; USGS Astrogeology. Public, attribution required.
- Earth: ESA Copernicus GLO-30 via OpenTopography. Free use with attribution.
- USGS 3DEP (optional): U.S. public domain.

Exact product IDs, versions, checksums, and citations are recorded in
`terratrace/sources.lock.yml` (generate with `scripts/make_source_lock.py`).
