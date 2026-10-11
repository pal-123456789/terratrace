#!/usr/bin/env python3
"""TerraTrace ANALOG ATLAS -- one command: MANY references x MANY candidates x ALL lenses.

A single study compares ONE planetary reference window against a slate of Earth
candidates under one decision lens. The atlas turns that into a systematic,
agency-usable catalog: it screens SEVERAL planetary reference windows against
SEVERAL candidate terrains under ALL FIVE decision lenses (core / extended /
geomorphic / landform / texture) and synthesises the whole grid into a ranked
LENS-ROBUSTNESS catalog -- which candidates stay Pareto non-dominated no matter
which reference and which morphology lens you pick.

It leans entirely on the tested engine: `batch.run_batch` (array-level, needs no
network or rasterio -- fully offline-testable) and `batch.run_real_batch` (loads
real DEMs via the shared loader). The output is a transparent robustness
synthesis, NOT a composite "Mars-likeness" score, and it inherits the claim
firewall: map-scale morphology only.

Three ways to run it, so the whole pipeline is exercisable OFFLINE and the REAL
download path stays one flag away on a networked machine:

  --dry-run    Preflight ONLY (offline): validate each unit's bbox/body, pick the
               catalog source that covers it, print an approximate request size,
               and exit 0 (clean) / 2 (problems). No network, no DEM reads.
  --synthetic  Deterministic OFFLINE surfaces (no fetch, no rasterio): one tilted
               plane + per-unit seeded roughness per unit, run through the SAME
               batch engine, so the atlas.json/atlas.md are produced and testable
               without any data.
  (default)    REAL mode: preflight, fetch any missing candidate DEMs from
               OpenTopography (needs OPENTOPO_API_KEY + rasterio; planetary
               reference DEMs must already be on disk), then run the real batch.

Pure standard library + the terratrace engine. PyYAML is imported LAZILY inside
_load_config only (the NumPy-only CI env has no yaml); rasterio is only touched on
the REAL path, via the engine, never under --dry-run / --synthetic.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import batch, preflight, synthetic

DEFAULT_MODES = ("core", "extended", "geomorphic", "landform", "texture")

HONEST_NOTE = (
    "NOTE: map-scale terrain-MORPHOLOGY screening across decision lenses only -- a "
    "lens-robustness synthesis, NOT a composite Mars-likeness score, and no "
    "traversability, geologic-equivalence, site-access, or mission-readiness claim.")

def _load_config(path):
    """Parse the YAML atlas config into a plain dict.

    PyYAML is imported LAZILY here (not at module top) so the engine's offline
    tests can drive run_from_config() with a plain dict without requiring PyYAML
    -- the NumPy-only CI env has no yaml (it ships in requirements-real).
    """
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _dry_run(cfg):
    """--dry-run: preflight every unit (offline). Return 0 (clean) / 2 (problems).

    Each unit is preflighted on ITS OWN body as a standalone `reference` (the
    schema preflight.preflight_config understands), so the atlas's legitimate
    reuse of one planetary DEM file across two reference windows is never flagged
    as a spurious "duplicate path". A cross-unit duplicate-ID guard is added on
    top because duplicate ids genuinely collide in run_batch's id-keyed units map.
    """
    tsm = float(cfg.get("target_support_m", 1000.0))
    refs = list(cfg.get("references") or [])
    cands = list(cfg.get("candidates") or [])
    print(f"[preflight] atlas sizing -- {len(refs)} reference(s) x {len(cands)} "
          f"candidate(s), target common support = {tsm:g} m")

    ok = True
    problems = []
    for kind, group in (("ref ", refs), ("cand", cands)):
        for u in group:
            rep = preflight.preflight_config({"target_support_m": tsm, "reference": u})
            for uid, info in rep["units"].items():
                src = (info.get("recommended_source") or {}).get("source_id")
                est = info.get("estimates") or {}
                size = (f"~{est['download_mb']:.1f} MB, ~{est['pixels']:,} px"
                        if est else "size n/a")
                print(f"  - [{kind}] {str(uid):28s} {'OK  ' if info['ok'] else 'FAIL'} "
                      f"source={src} {size}")
                for w in info.get("warnings", []):
                    print(f"        ! warning: {w}")
            if not rep["ok"]:
                ok = False
            problems.extend(rep["problems"])

    # Genuinely fatal cross-unit checks the per-unit preflight cannot see.
    if not refs or not cands:
        problems.append("atlas: need at least one reference and one candidate")
        ok = False
    ids = [u.get("id") for u in (refs + cands)]
    for d in sorted({i for i in ids if i is not None and ids.count(i) > 1}):
        problems.append(f"atlas: duplicate unit id {d!r} (ids must be unique across the atlas)")
        ok = False

    if problems:
        print("[preflight] PROBLEMS:")
        for p in problems:
            print(f"      x {p}")
    else:
        print("[preflight] no hard problems.")
    return 0 if ok else 2


def _synthetic_report(cfg, refs, cands, modes):
    """--synthetic: build a deterministic surface per unit (references + candidates)
    and run the SAME batch engine on them (no fetch, no rasterio).

    Every unit gets one gently tilted plane plus seeded roughness. References share
    a common baseline amplitude; the first candidate matches it (nearest analog)
    and each later candidate is markedly rougher, so the candidates genuinely
    differ and the lens-robustness synthesis produces a real ordering offline.
    """
    tsm = float(cfg.get("target_support_m", 1000.0))
    all_units = list(refs) + list(cands)
    n_ref = len(refs)
    arrays = {}
    for i, u in enumerate(all_units):
        if i < n_ref:
            amp = 30.0                       # references: common baseline roughness
        else:
            j = i - n_ref                    # candidate position (0-based)
            amp = 30.0 if j == 0 else 30.0 + 25.0 * j
        z = (synthetic.plane((80, 80), slope_x=0.02, dx=tsm)
             + synthetic.rough_field((80, 80), amp, seed=i))
        arrays[u["id"]] = z
    return batch.run_batch(
        arrays, [r["id"] for r in refs], [c["id"] for c in cands],
        native_posting_m=tsm, target_support_m=tsm, decision_modes=modes,
        source_label="atlas_synthetic")


def _fetch_missing(cfg):
    """REAL mode: download any candidate DEM not already on disk, exactly as
    scripts/run_real_analog_study.py does (OpenTopography global DEM or USGS 3DEP
    via the same free key). Planetary REFERENCE windows are cropped from a DEM
    downloaded once from USGS Astrogeology; they are never fetched here -- a
    missing reference prints the download instruction and aborts."""
    from terratrace import ingest
    key = os.environ.get("OPENTOPO_API_KEY")
    if not key:
        sys.exit("Set OPENTOPO_API_KEY (free key: https://portal.opentopography.org).")
    for ref in cfg.get("references", []):
        if not os.path.exists(ref["path"]):
            sys.exit(
                f"Reference DEM missing: {ref['path']} (id={ref.get('id')})\n"
                "  Planetary reference DEMs (e.g. Mars MGS MOLA 463m, Moon LRO LOLA) are\n"
                "  downloaded once from USGS Astrogeology:\n"
                "    https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m\n"
                "  save it to that path, then re-run (atlas references crop windows from it).")
    for unit in cfg.get("candidates", []):
        out = unit["path"]
        if os.path.exists(out):
            print(f"[=] {unit['id']} present: {out} -- skipping")
            continue
        os.makedirs(os.path.dirname(out) or ".", exist_ok=True)
        bbox = unit["bbox"]  # west, south, east, north
        dataset = unit.get("dataset")
        if dataset:
            print(f"[*] fetching {unit['id']} 3DEP {dataset} bbox={bbox} -> {out}")
            ingest.fetch_usgs_3dep(bbox, key, out, dataset=dataset)
        else:
            demtype = unit.get("demtype", "COP30")
            print(f"[*] fetching {unit['id']} {demtype} bbox={bbox} -> {out}")
            ingest.fetch_opentopo_global(bbox, key, out, demtype=demtype)
        print(f"    done: {out}")


def _real_report(cfg, modes, skip_fetch):
    """REAL mode: preflight (abort on hard problems), fetch missing candidate DEMs
    (unless --skip-fetch), verify every reference+candidate file is on disk, then
    run the real batch over the whole grid. Requires rasterio."""
    refs = list(cfg.get("references") or [])
    cands = list(cfg.get("candidates") or [])
    if _dry_run(cfg) != 0:
        sys.exit("[preflight] aborting: fix the problems above "
                 "(adjust bboxes / bodies / ids in the config) and re-run.")
    if not skip_fetch:
        _fetch_missing(cfg)
    units = refs + cands
    missing = [u["path"] for u in units if not os.path.exists(u["path"])]
    if missing:
        sys.exit("Missing DEM files (fetch on a networked machine, or drop "
                 "--skip-fetch):\n  " + "\n  ".join(missing))
    return batch.run_real_batch(
        units, target_support_m=float(cfg.get("target_support_m", 1000.0)),
        min_valid=cfg.get("min_valid_fraction", 0.5),
        reproject=cfg.get("reproject", True), decision_modes=modes,
        references=[r["id"] for r in refs])


def _fmt_mean_layer(x):
    """Format a mean Pareto layer, rendering NaN (a never-ranked candidate) as n/a."""
    return f"{x:.2f}" if isinstance(x, (int, float)) and x == x else "n/a"


def render_atlas_md(report):
    """Render the batch report as a Markdown lens-robustness CATALOG.

    Title + firewall line, a reference-agnostic synthesis table of every candidate
    in `robust_ordering` (columns: candidate / layer1_frequency % /
    recommended_frequency % / mean_layer / consensus ✓), the consensus shortlist,
    and the verbatim engine note. This is a robustness synthesis, NOT a composite
    score -- the honesty is in the columns, not in a single number.
    """
    pc = report["per_candidate"]
    consensus = set(report["consensus_shortlist"])
    L = []
    L.append("# TerraTrace Analog Atlas")
    L.append("")
    L.append(f"_{HONEST_NOTE}_")
    L.append("")
    L.append(f"- references screened: {len(report['references'])} "
             f"({', '.join(report['references'])})")
    L.append(f"- candidates screened: {len(report['candidates'])}")
    L.append(f"- decision lenses: {', '.join(report['decision_modes'])}")
    L.append(f"- (reference x lens) cells: {report['n_cells']}")
    L.append(f"- package_hash: `{report.get('package_hash', '')}`")
    L.append("")
    L.append("## Lens-robustness synthesis (reference-agnostic)")
    L.append("")
    L.append("Candidates ordered by how often they are Pareto **non-dominated** "
             "across ALL (reference x decision-lens) cells. `layer1_frequency` is "
             "that fraction; `recommended_frequency` is how often the candidate is "
             "the sole recommendation; `mean_layer` is the mean Pareto layer "
             "(1 = non-dominated; lower is better).")
    L.append("")
    L.append("| rank | candidate | layer1_frequency | recommended_frequency | mean_layer | consensus |")
    L.append("|---:|---|---:|---:|---:|:--:|")
    for i, c in enumerate(report["robust_ordering"], 1):
        m = pc[c]
        L.append(f"| {i} | {c} | {m['layer1_frequency'] * 100:.0f}% | "
                 f"{m['recommended_frequency'] * 100:.0f}% | {_fmt_mean_layer(m['mean_layer'])} | "
                 f"{'✓' if c in consensus else ''} |")
    L.append("")
    L.append("## Consensus shortlist")
    L.append("")
    if report["consensus_shortlist"]:
        L.append("Candidates Pareto non-dominated in **every** cell -- robust to both the "
                 "choice of reference and the choice of morphology lens:")
        L.append("")
        for c in report["consensus_shortlist"]:
            L.append(f"- **{c}**")
    else:
        L.append("_No candidate is non-dominated in every cell -- the best analog is "
                 "reference- and/or lens-dependent (read the table above)._")
    L.append("")
    L.append("## Note")
    L.append("")
    L.append(f"> {report['note']}")
    L.append("")
    return "\n".join(L)


def _print_summary(report, out):
    """Print the one-screen lens-robustness catalog (honest, no composite score)."""
    pc = report["per_candidate"]
    consensus = set(report["consensus_shortlist"])
    print("")
    print("=" * 78)
    print("TerraTrace analog atlas -- lens-robustness catalog")
    print("=" * 78)
    print(f"references = {len(report['references'])}   "
          f"candidates = {len(report['candidates'])}   "
          f"lenses = {', '.join(report['decision_modes'])}   "
          f"cells = {report['n_cells']}")
    print(f"package_hash = {str(report.get('package_hash', ''))[:16]}...")
    print(f"{'rank':<5}{'candidate':<30}{'layer1%':>9}{'recommend%':>12}"
          f"{'mean_layer':>12}  consensus")
    print("-" * 78)
    for i, c in enumerate(report["robust_ordering"], 1):
        m = pc[c]
        print(f"{i:<5}{c[:29]:<30}{m['layer1_frequency'] * 100:>8.0f}%"
              f"{m['recommended_frequency'] * 100:>11.0f}%"
              f"{_fmt_mean_layer(m['mean_layer']):>12}"
              f"  {'YES' if c in consensus else '-'}")
    print("-" * 78)
    print(f"consensus_shortlist = {report['consensus_shortlist'] or '(none)'}")
    print(f"bundle = {out}  [atlas.json, atlas.md]")


def _finish(report, out):
    """Write atlas.json (full report) + atlas.md (catalog), print the summary +
    the honest note. Return 0."""
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "atlas.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    with open(os.path.join(out, "atlas.md"), "w", encoding="utf-8") as fh:
        fh.write(render_atlas_md(report))
    _print_summary(report, out)
    print(HONEST_NOTE)
    return 0


def run_from_config(cfg, out="artifacts/atlas", dry_run=False, synthetic=False,
                    skip_fetch=False):
    """Drive the whole atlas from an already-parsed config DICT.

    Factored out of main() with NO YAML/file I/O so the orchestration is
    unit-testable offline without PyYAML. Returns an exit code (0 = clean;
    --dry-run returns 0/2). REAL mode may sys.exit on a missing key / DEM.
    """
    modes = tuple(cfg.get("decision_modes") or DEFAULT_MODES)
    if dry_run:
        return _dry_run(cfg)
    refs = list(cfg.get("references") or [])
    cands = list(cfg.get("candidates") or [])
    if synthetic:
        print("[mode] synthetic (deterministic offline surfaces)")
        report = _synthetic_report(cfg, refs, cands, modes)
    else:
        print("[mode] real (download + rasterio)")
        report = _real_report(cfg, modes, skip_fetch)
    return _finish(report, out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="TerraTrace analog atlas: screen many planetary references "
                    "against many candidates across all five decision lenses and "
                    "emit a ranked lens-robustness catalog (morphology screening only).")
    ap.add_argument("--config", required=True,
                    help="atlas config YAML (see config/analog_atlas.example.yml)")
    ap.add_argument("--out", default="artifacts/atlas", help="output catalog directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="preflight only (offline); no fetch, no DEM reads; exit 0/2")
    ap.add_argument("--synthetic", action="store_true",
                    help="deterministic offline surfaces (no fetch, no rasterio)")
    ap.add_argument("--skip-fetch", action="store_true",
                    help="REAL mode: assume DEMs are already on disk; do not download")
    args = ap.parse_args(argv)
    cfg = _load_config(args.config)
    return run_from_config(cfg, out=args.out, dry_run=args.dry_run,
                           synthetic=args.synthetic, skip_fetch=args.skip_fetch)


if __name__ == "__main__":
    raise SystemExit(main())
