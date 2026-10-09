# 03 — Data and Source Contracts

## Data principles

1. Sources are leads until exact product/version/terms are verified.
2. Every data field carries units, support, coordinate frame, quality, and provenance.
3. The prepared public demo uses pinned compact artifacts and does not require a live API.
4. Source files are not redistributed unless terms permit it.
5. Data availability never implies access permission or field authorization.
6. Data resolution is not treated as truth at scales it does not resolve.

## Source candidates

| Candidate source | Intended role | Primary entry point | G1 question | v0.1 status until verified |
|---|---|---|---|---|
| MGS MOLA MEGDR | Mars regional topographic reference | [PDS MOLA MEGDR](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | Which exact grid, map projection, pixel support, vertical datum, coverage, product release, and terms? | U0 |
| Higher-resolution Mars terrain product | Optional local context if a suitable product exists | [PDS Geosciences](https://pds-geosciences.wustl.edu/) | Exact product, coverage, DTM vs image, uncertainty, processing, redistribution? | U0 |
| USGS 3DEP | Earth DEM in eligible US region | [3DEP](https://www.usgs.gov/3d-elevation-program), [National Map downloads](https://www.usgs.gov/the-national-map-data-delivery/gis-data-download) | Exact tile/product/collection, acquisition, bare-earth vs surface, accuracy, CRS, terms? | U0 |
| Copernicus DEM | Global Earth backup | [Copernicus DEM](https://dataspace.copernicus.eu/explore-data/data-collections/copernicus-digital-elevation-model) | Current access/terms, GLO product version, effective support, void/quality metadata? | U0 |
| Landsat/Sentinel imagery | Context only | [NASA Earthdata Search](https://search.earthdata.nasa.gov/), [Sentinel-2](https://sentinel.esa.int/web/sentinel/missions/sentinel-2) | Is imagery used quantitatively or only as context? Acquisition/cloud/illumination metadata? | U0 |
| Site constraints | Access/protected area/ecology metadata | Relevant local authority/source selected per unit | Is publication appropriate? Does it establish access or only a restriction? | U0 |

**No site is preselected as a field site.** Mauna Kea, Lanzarote, Atacama, and other analog-famous locations are candidate search regions only. G1 chooses bounded units based on source evidence, not brand recognition.

## Source-lock schema

```yaml
source_id: string
provider: string
product_name: string
product_id: string
release_or_version: string
source_url: string
retrieved_at: ISO-8601
sha256: hex
license_url: URL
redistribution_status: allowed | derived_only | no | unknown
body: mars | earth
spatial_crs: string
vertical_datum: string
units: string
native_posting_m: number | unknown
effective_support_m: number | unknown
coverage: geometry_ref
acquisition_or_processing_time: string | unknown
quality_mask: string
nodata_policy: string
metadata_checked_by: string
claim_status: U0 | S1 | M2 | C3 | R4
limitations: [string]
```

Unknown fields remain explicit. Do not fill them from a secondary summary if the product label contains the answer.

## AOI contract

Each terrain unit is a bounded polygon with:

- unique ID;
- body and geographic/planetary CRS;
- analysis extent and buffer;
- equal-area or otherwise justified comparison policy;
- inclusion/exclusion criteria;
- data coverage ratio;
- source footprint intersection;
- publication sensitivity flag;
- field access status (unknown unless verified).

Compare equivalent **terrain units**, not entire named regions. If unit area differs, document whether features are area-weighted, sampled, or distributional.

## Effective-support decision

For every dataset, record:

- raster posting/pixel spacing;
- effective spatial resolution if documented;
- vertical accuracy/uncertainty if documented;
- observation footprint;
- source processing and gridding;
- analysis window in metres;
- aggregation method;
- minimum feature scale.

If effective support is unknown, use a conservative declared rule and mark the result accordingly. Do not claim precise physical scale from posting alone.

## Data volume and packaging

- Preserve raw data in an external cache or user-retrieval directory during preparation; do not place challenge-derived outputs in a pre-event submission repository.
- After kickoff, produce small derivative artifacts only where source terms permit.
- Record raw-file checksums, but avoid committing large raw datasets.
- Publicly distribute derived data only if source terms permit; otherwise publish identifiers, retrieval procedure, environment lock, and reproducible transformations.
- Keep a static canonical artifact bundle below an agreed release budget, initially 10 MB compressed; measure rather than assume.

## Data quality and masking

Every metric calculation must state how it handles:

- nodata;
- edge effects;
- small holes;
- void-filled values;
- slope artifacts;
- tile seams;
- mixed collection dates;
- vertical-datum mismatch;
- resampling;
- projected-distance distortion;
- source quality flags.

No silent zero-fill. No interpolation across a scientifically meaningful gap without flagging it.

## Data lineage

```text
source product + label
  → checksum and license record
  → AOI extraction
  → coordinate transform
  → quality mask
  → common-support aggregation
  → feature computation
  → sensitivity scenario
  → result artifact
  → UI field / claim
```

## G1 data feasibility checklist

Pass only if one Mars unit and at least two Earth units have:

- exact product IDs and files;
- usable coverage;
- checked coordinate/datum metadata;
- declared native and analysis support;
- source terms and redistribution plan;
- reproducible AOI bounds;
- a non-silent nodata policy;
- no critical feature that depends on unsupported resolution.

Otherwise do not rank. Pivot to a transfer-audit demonstrator.
