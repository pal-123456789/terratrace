# Lunar status: supported by the engine, not yet demonstrated on real terrain

The challenge is about **both** the Moon and Mars: *"Identify Earth Locations that Analog the
Permanent Moon Base Locations and Mars."* TerraTrace's headline v3 result is Mars-only. This page
records exactly where the lunar half stands, so nobody has to guess — and so nobody reads a
capability as a result.

**Summary: the data blocker is RESOLVED for one site. Real lunar terrain has been ingested and
analysed (exploratory) — see [`LUNAR-DEMONSTRATION.md`](LUNAR-DEMONSTRATION.md). No confirmatory
lunar finding is claimed, and no uncertainty propagation has been done yet.**

## 1. What the engine genuinely supports (verified in code)

The Moon is a first-class body throughout the engine, not a stub:

| path | lunar value |
|---|---|
| `reproject.body_radius_m("moon")` | 1 737 400 m |
| `reproject.geographic_crs("moon")` | `+proj=longlat +a=1737400.0 +b=1737400.0 +no_defs` |
| `reproject.local_aeqd(lat, lon, "moon")` | a valid lunar azimuthal-equidistant metric CRS |
| catalog `moon_lola_ldem` | body `moon`, native posting **118 m**, global coverage, `valid_resolution_range_m` 118–500 000 |
| citation | Smith et al., LRO LOLA LDEM; USGS Astrogeology lunar LDEM 118 m |

So the ingest, the body-aware reprojection, the common-support step, the descriptors and the
decision layer are all lunar-capable. At a 118 m native posting, a 60 km window is ~508 cells per
side and the study's 1 500 m honest support is comfortably reachable — the *method* would work.

## 2. Why no demonstration was produced *at the time of writing* — since RESOLVED

> **Update 2026-11-13:** the Goddard PGDA archive in §4 turned out to serve 5 m/pixel
> south-polar products at 41 MB per file, and one was retrieved and analysed. The text below
> is kept as the record of what the position was before that, because the reasoning about
> dead endpoints and honest blockers is still the right reasoning.


Three reasons, in order of force. The first is decisive on its own.

**(a) The catalogued access endpoint is dead.** `moon_lola_ldem` points at
`https://astrogeology.usgs.gov/search/map/lunar_lro_lola_global_ldem_118m`. Fetched on
2026-11-13, that path returns an HTTP 200 whose body is the USGS Astrogeology **"Error 404: This
page cannot be found"** page. A direct request from the command line is refused with HTTP 403
(Cloudflare), so the failure is reproducible but not diagnosable from here. **This is a defect in
the shipped catalog and is recorded as such in `CLAIM-LEDGER.md`** — a source entry that a reader
cannot resolve. The correct path could not be established in this environment; a web search for
the product returned no usable result.

**(b) No lunar elevation data is present.** The working tree contains `data/earth/` and
`data/mars/` only. Nothing lunar has ever been downloaded here, and the fetch that would obtain
it is the same fetch as (a).

**(c) The global product is far beyond this environment's capacity even if it were reachable.**
A 118 m global lunar DEM is a multi-gigabyte raster. This session runs on a 2-CPU sandbox with no
large-file budget, and the project's own rule for the Mars side is to *window* the 2.1 GB global
MOLA rather than load it whole — a discipline that requires first knowing a working endpoint.

## 3. What was deliberately NOT done

- **No invented Moon-base coordinates.** The official challenge does not specify precise lunar
  reference sites. Naming one would have meant choosing a location myself and presenting it as
  authoritative.
- **No substitute dataset dressed up as a lunar demonstration.** A synthetic Moon would have
  produced a green run and proved nothing about the challenge.
- **No claim of morphological resemblance as base *suitability*.** Even with data, that inference
  is outside the engine's claim firewall — base siting involves illumination, thermal environment,
  regolith mechanics, communications geometry and surface access, none of which this project
  measures. A lunar morphology comparison could at most screen terrain *shape*.

## 4. What would unblock it

Any one of these, in order of preference:

1. A corrected USGS Astrogeology or PDS Geosciences endpoint for the LOLA LDEM product, or a
   confirmed tiled subset so a windowed read is possible (the same pattern as the keyless
   Copernicus COG path that unblocked the Earth side).
2. Any public lunar DEM at better than ~500 m posting with a resolvable URL, which would allow a
   genuine comparison at the study's existing 1 500 m support.
3. A coarser product (for example 4 or 16 pixels per degree) used honestly at a *coarser common
   support* — both bodies aggregated to the same support — clearly labelled exploratory, with the
   coarser scale stated in the result. This would be a weaker result than the Mars panel and should
   be described as such.

## 5. How the lunar half is represented in the submission

Since the Goddard products were retrieved, the lunar half is described as **supported, and
demonstrated on real terrain in an exploratory capacity**. The exploratory result is on
[`LUNAR-DEMONSTRATION.md`](LUNAR-DEMONSTRATION.md); it is never presented as confirmatory, and no
lunar base-suitability claim is made anywhere. The deck's limitations slide names the remaining
gaps (no uncertainty propagation, one site, three declared axes rather than the frozen lens) rather
than leaving a judge to discover them. This is the same treatment the project gives its other open
items: named first, not buried.

## 6. Status classification

| item | status |
|---|---|
| Lunar body support in the engine | **IMPLEMENTED AND TESTED** (body metadata, CRS, catalog entry) |
| Lunar data acquisition | **PARTLY RESOLVED** — the catalogued USGS LDEM endpoint still 404s; the Goddard PGDA 5 m/px products *do* serve, and Site01's elevation raster was retrieved |
| Lunar comparison on real terrain | **DONE, EXPLORATORY** — one site, three declared axes; see [`LUNAR-DEMONSTRATION.md`](LUNAR-DEMONSTRATION.md) |
| Lunar uncertainty propagation | **NOT STARTED** — the published uncertainty rasters were not retrieved |
| Lunar confirmatory protocol | **NOT STARTED** — would require a frozen v4 |
| Lunar claim in any published result | **exploratory only**; no confirmatory or base-suitability claim |
