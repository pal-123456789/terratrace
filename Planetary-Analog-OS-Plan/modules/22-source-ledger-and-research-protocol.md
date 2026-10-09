# 22 — Source Ledger and Research Protocol

## Purpose

This ledger separates what is known from what must be checked. A source entry is not a claim until exact artifact metadata and terms are verified.

## Initial primary entry points

| Domain | Source | Use | Status |
|---|---|---|---|
| Event | [Space Apps 2026 event page](https://www.spaceappschallenge.org/2026/) | Dates/submission | Capture/verify |
| Terms | [Participant Terms](https://www.spaceappschallenge.org/legal/) | Eligibility, citation, licensing | Capture/verify |
| Guidance | [Official 2026 local-event guidance](https://www.spaceappschallenge.org/2026/local-events/santiago-dominican-republic/) | Pre-event conduct | Capture/verify |
| Judging | [2026 local event](https://www.spaceappschallenge.org/2026/local-events/ajmer/) | Criteria entry point | Capture exact wording |
| Challenge context | [2026 analog team page](https://www.spaceappschallenge.org/2026/find-a-team/lunar-terra/) | Challenge description context | Use as corroboration, prefer challenge page |
| Mars topography | [PDS MOLA](https://pds-geosciences.wustl.edu/missions/mgs/mola.html) | Product discovery | Product-level check required |
| MOLA grids | [PDS MOLA MEGDR](https://pds-geosciences.wustl.edu/missions/mgs/megdr.html) | Exact product family | Product/version check |
| Lunar topography | [PDS LOLA](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) | Future Moon module | Not v0.1 critical |
| Earth DEM | [USGS 3DEP](https://www.usgs.gov/3d-elevation-program) | Earth terrain source | Exact tile/product check |
| USGS access | [National Map downloads](https://www.usgs.gov/the-national-map-data-delivery/gis-data-download) | Product retrieval | Exact endpoint/check |
| Earth discovery | [NASA Earthdata Search](https://search.earthdata.nasa.gov/) | Optional context products | Not critical until tested |
| Catalog standard | [STAC](https://stacspec.org/en/) | Metadata/catalog model | Standards reference |

## Research capture template

```markdown
# Source: <name>

- URL:
- Provider:
- Retrieved at:
- Product ID:
- Version/release:
- Exact file:
- SHA-256:
- Coverage:
- CRS:
- Vertical datum:
- Native posting:
- Effective support:
- Quality flags:
- No-data policy:
- Terms/license URL:
- Redistribution status:
- Citation text:
- Claim supported:
- Claim not supported:
- Reviewer:
- Status: U0/S1/M2/C3/R4
- Open questions:
```

## Research sequence

1. Capture official event/rules evidence.
2. Locate exact Mars product candidate and label.
3. Inspect coverage and coordinate/datum metadata.
4. Determine terms/redistribution path.
5. Locate Earth products covering bounded candidate units.
6. Compare effective support and quality.
7. Reject any candidate that requires unsupported feature scale.
8. Freeze source lock before calculation.
9. Compute fixtures and independent checks.
10. Upgrade claims only after outputs and reviewers agree.

## Source hierarchy

1. Official product label/metadata.
2. Official provider documentation.
3. Peer-reviewed or authoritative technical paper.
4. Official catalog entry.
5. Secondary summary only for discovery.
6. Search snippet only as a lead.

## Citation requirements

Every published number/statement includes:

- provider and product;
- product/version;
- retrieval/access time;
- transformation/method reference;
- terms/attribution;
- uncertainty/limitation;
- claim status.

## Research stop conditions

Stop source acquisition when:

- exact product cannot be verified;
- coordinate/datum ambiguity remains;
- effective support is unknown and material to the claim;
- terms do not permit planned use;
- source is not reproducible;
- source is being used only because it makes the result look impressive.

## Planned evidence status at project start

All entries begin U0 in the implementation project. The plan library is not itself evidence that a product was retrieved or that a scientific result exists.
