# data/mars

The global **MGS MOLA 463 m** DEM (`mola_463m.tif`, ~2 GB) lives here on your machine but
is **git-ignored** — it exceeds GitHub's 100 MB per-file limit, so it cannot be pushed.

Two ways to populate this folder:

1. **Full global DEM (local only).** Download "Mars MGS MOLA DEM 463m" GeoTIFF from
   USGS Astrogeology and save it as `mola_463m.tif`:
   https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m

2. **Small committable AOI sample.** After step 1, crop the study window into a few-MB
   GeoTIFF that *can* live in the repo:
   ```bash
   python scripts/make_mars_sample.py --config config/aois.example.yml
   # -> data/mars/mola_sample.tif  (committable)
   ```

Source: NASA PDS / MGS MOLA MEGDR; USGS Astrogeology. Public data, attribution required.
