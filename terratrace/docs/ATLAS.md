# TerraTrace Analog Atlas

Screen **many** planetary reference terrains against **many** Earth candidates across **all five
decision lenses** in one command, and get a ranked, lens-robustness *catalog* instead of a single
comparison.

> **Scope / claim firewall.** A lens-robustness synthesis of map-scale terrain *morphology* only
> — NOT a composite "likeness" score, and not a traversability, geologic-equivalence, site-access,
> or mission-readiness claim. The Earth sites are illustrative analogs, not endorsed field sites.

## Run it (on the DEMs you already fetched)

```bash
py scripts/run_analog_atlas.py --config config/analog_atlas.example.yml --skip-fetch
```

The example screens two Mars MOLA windows against the three Earth candidates already on disk
(Nevada basin, Craters of the Moon, Andean volcano) under **core / extended / geomorphic /
landform / texture**. The bundle lands in `artifacts/atlas/`: `atlas.json`, `atlas.md`, and a printed table.

- See it offline with no data: add `--synthetic`.
- Validate a config with zero network: `--dry-run`.

## What it reports

For each candidate, across every (reference × lens) cell:

- **layer1_frequency** — fraction of cells where it is Pareto non-dominated (the best tier);
- **recommended_frequency** — fraction where it is the sole recommendation;
- **mean_layer** — mean Pareto layer (1 = best);
- **consensus** — non-dominated in *every* cell, i.e. robust to both the choice of reference and
  the choice of morphology lens.

A candidate on the **consensus shortlist** is a robust morphological analog across references and
lenses. The catalog never collapses this into one number — robustness is reported as frequencies.

## Scale-up

Add more reference windows (e.g. Jezero, Gale, a lunar mare via LOLA, a Mercury plain) and more
candidates to the config and re-run; the atlas grows into a systematic, reproducible cross-world
analog catalog with honest uncertainty. See `docs/PAPER.md` and `REAL-DATA-RUNBOOK.md`.
