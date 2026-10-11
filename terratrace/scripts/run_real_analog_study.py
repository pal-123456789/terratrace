#!/usr/bin/env python3
"""ONE-COMMAND real multi-body analog study for TerraTrace.

Takes a single AOI config and produces a FULL result bundle in one directory:
the JSON study package, a Markdown + self-contained HTML report, the offline
viewer, a REFERENCES credits file, a CHECKSUMS manifest, and a confidence.json
decision-confidence summary.

Three ways to run it, so the whole pipeline is exercisable OFFLINE here and the
REAL download path stays one flag away on a networked machine:

  --dry-run    Preflight ONLY (offline): validate the config schema + every
               bbox, pick the catalog source that covers each AOI, print an
               approximate request size, and exit 0 (clean) / 2 (problems).
               No network, no DEM reads.
  --synthetic  Deterministic OFFLINE surfaces (no fetch, no rasterio): build one
               tilted plane + per-unit roughness per unit and run the SAME
               comparison engine, so the bundle/report/viewer/confidence are all
               produced and testable without any data.
  (default)    REAL mode: preflight, fetch any missing Earth DEMs from
               OpenTopography (needs OPENTOPO_API_KEY + rasterio; the Mars MOLA
               reference must already be on disk), then run the real study.

Two reporting modes layer on top (same inputs, obtained once, no extra fetch):

  --decision-metrics L  Override the config's decision lens (core / extended /
               geomorphic / landform / texture) for the single study it would otherwise run.
  --ablation   Run the decision under ALL FIVE lenses on ONE dataset and report
               what each concludes. The "best analog" is lens-dependent -- a
               Pareto TIE under one lens can resolve under another -- so a single
               run surfaces the full tie-break. Prints a table + writes ablation.json.

Scientific boundary (claim firewall): map-scale terrain-MORPHOLOGY screening and
resampling statistics only. Nothing here is a traversability, geologic-
equivalence, site-access, or mission-readiness claim.

Pure standard library + PyYAML + the terratrace engine. rasterio is only touched
on the REAL path (lazily, via the engine), never in --dry-run / --synthetic.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import study, bundle, confidence, preflight, synthetic

HONEST_NOTE = ("NOTE: map-scale terrain-MORPHOLOGY screening + resampling statistics only -- "
               "no traversability, geologic-equivalence, site-access, or mission-readiness claim.")

def _load_config(path):
    """Parse the YAML AOI config into a plain dict.

    PyYAML is imported LAZILY here (not at module top) so the engine's offline
    tests can drive run_from_config() with a plain dict without requiring PyYAML
    -- the NumPy-only CI environment has no yaml (it ships in requirements-real).
    """
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _study_kwargs(cfg):
    """Read the optional depth/decision flags off the config, with safe defaults,
    exactly as the engine expects them. These are passed through unchanged to both
    the synthetic (compare_units) and real (run_real_study) front doors."""
    return {
        "decision_metrics": cfg.get("decision_metrics", "core"),
        "n_boot": int(cfg.get("n_boot", 0)),
        "significance": bool(cfg.get("significance", False)),
        "n_perm": int(cfg.get("n_perm", 1000)),
        "landform": bool(cfg.get("landform", False)),
        "terrain_spectra": bool(cfg.get("terrain_spectra", False)),
        "previews": bool(cfg.get("previews", False)),
    }


def _print_preflight(report):
    """Human-readable preflight report: target support, per-unit ok/source/size,
    advisory warnings, and any hard problems."""
    print(f"[preflight] target common support = {report['target_support_m']:g} m")
    for uid, u in report["units"].items():
        rec = u.get("recommended_source") or {}
        est = u.get("estimates") or {}
        src = rec.get("source_id")
        size = (f"~{est['download_mb']:.1f} MB, ~{est['pixels']:,} px" if est else "size n/a")
        print(f"  - {uid:28s} {'OK  ' if u['ok'] else 'FAIL'} source={src} {size}")
        for w in u.get("warnings", []):
            print(f"      ! warning: {w}")
    if report["problems"]:
        print("[preflight] PROBLEMS:")
        for p in report["problems"]:
            print(f"      x {p}")
    else:
        print("[preflight] no hard problems.")


def _dry_run(cfg):
    """--dry-run: preflight only (offline). Return 0 (clean) / 2 (problems)."""
    report = preflight.preflight_config(cfg)
    _print_preflight(report)
    return 0 if report["ok"] else 2

def _synthetic_inputs(cfg):
    """Build the deterministic OFFLINE comparison inputs ONCE (no fetch, no
    rasterio) so the SAME surfaces feed either a single study (_synthetic_package)
    or the five-lens ablation. Returns (raw, rights, reference_id, target_support_m).

    Each unit gets one gently tilted plane plus seeded roughness. The roughness
    amplitude follows a per-unit ladder (reference smoothest; the first Earth
    candidate closest to it, the rest progressively rougher) so the candidates
    genuinely differ and one is clearly nearest the reference -- enough for the
    decision/significance/confidence machinery to produce a real verdict offline.
    """
    tsm = float(cfg.get("target_support_m", 1000.0))
    units = [cfg["reference"]] + list(cfg.get("earth_units", []))
    reference_id = next((u["id"] for u in units if u.get("is_reference")),
                        units[0]["id"])
    raw, rights = {}, {}
    for i, u in enumerate(units):
        # Roughness amplitude (metres) ladder. The reference and candidate_a share
        # the same amplitude (different seed -> nearest realization), and each
        # later candidate is markedly rougher. The amplitude is large enough at
        # this support to drive real slope/relief/ruggedness differences, so
        # candidate_a is the sole Pareto-non-dominated unit -- a clean, non-TIE
        # recommendation for the offline demo (not a tuned result).
        amp = 30.0 if i <= 1 else 30.0 + 25.0 * (i - 1)
        z = (synthetic.plane((80, 80), slope_x=0.02, dx=tsm)
             + synthetic.rough_field((80, 80), amp, seed=i))
        raw[u["id"]] = z
        rights[u["id"]] = u.get("rights_status", "verified_allowed")
    return raw, rights, reference_id, tsm


def _synthetic_package(cfg):
    """--synthetic: build the deterministic OFFLINE surfaces (via _synthetic_inputs)
    and run the real comparison engine on them (no fetch, no rasterio, no
    run_real_study), honoring the config's depth/decision flags."""
    raw, rights, reference_id, tsm = _synthetic_inputs(cfg)
    kw = _study_kwargs(cfg)
    return study.compare_units(
        raw, rights, native_posting_m=tsm, reference_id=reference_id,
        target_support_m=tsm, decision_metrics=kw["decision_metrics"],
        n_boot=kw["n_boot"], significance=kw["significance"], n_perm=kw["n_perm"],
        landform=kw["landform"], terrain_spectra=kw["terrain_spectra"],
        previews=kw["previews"])

def _fetch_missing(cfg):
    """REAL mode: download any Earth DEM not already on disk, exactly as
    scripts/fetch_real_dems.py does (OpenTopography global DEM or USGS 3DEP via
    the same free key). The Mars MOLA reference is NOT fetched here -- it must
    already exist (print the USGS download instruction and abort if missing)."""
    from terratrace import ingest
    key = os.environ.get("OPENTOPO_API_KEY")
    if not key:
        sys.exit("Set OPENTOPO_API_KEY (free key: https://portal.opentopography.org).")
    ref = cfg["reference"]
    if not os.path.exists(ref["path"]):
        sys.exit(
            f"Mars reference DEM missing: {ref['path']}\n"
            "  Download 'Mars MGS MOLA DEM 463m' (GeoTIFF) from USGS Astrogeology:\n"
            "  https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m\n"
            "  and save it to that path, then re-run.")
    for unit in cfg.get("earth_units", []):
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


def _real_package(cfg, skip_fetch):
    """REAL mode: preflight (abort on hard problems), fetch missing Earth DEMs
    (unless --skip-fetch), then run the real study. Requires rasterio."""
    report = preflight.preflight_config(cfg)
    _print_preflight(report)
    if not report["ok"]:
        sys.exit("[preflight] aborting: fix the problems above "
                 "(adjust bboxes / bodies / paths in the config) and re-run.")
    if not skip_fetch:
        _fetch_missing(cfg)
    units = [cfg["reference"]] + list(cfg.get("earth_units", []))
    missing = [u["path"] for u in units if not os.path.exists(u["path"])]
    if missing:
        sys.exit("Missing DEM files (fetch on a networked machine, or drop "
                 "--skip-fetch):\n  " + "\n  ".join(missing))
    kw = _study_kwargs(cfg)
    return study.run_real_study(
        units,
        target_support_m=float(cfg.get("target_support_m", 1000.0)),
        min_valid=cfg.get("min_valid_fraction", 0.5),
        reproject=cfg.get("reproject", True),
        decision_metrics=kw["decision_metrics"], n_boot=kw["n_boot"],
        previews=kw["previews"], landform=kw["landform"],
        significance=kw["significance"], n_perm=kw["n_perm"],
        terrain_spectra=kw["terrain_spectra"])


def _real_inputs(cfg, skip_fetch):
    """REAL-mode comparison inputs for the ablation: preflight (abort on hard
    problems, same gate as _real_package), fetch any missing Earth DEMs unless
    skip_fetch, verify every file is on disk, then load the units ONCE via
    study.load_real_units (rasterio). Returns (raw, rights, native, reference_id,
    target_support_m) -- native is the per-unit posting map from the loader."""
    report = preflight.preflight_config(cfg)
    _print_preflight(report)
    if not report["ok"]:
        sys.exit("[preflight] aborting: fix the problems above "
                 "(adjust bboxes / bodies / paths in the config) and re-run.")
    if not skip_fetch:
        _fetch_missing(cfg)
    units = [cfg["reference"]] + list(cfg.get("earth_units", []))
    missing = [u["path"] for u in units if not os.path.exists(u["path"])]
    if missing:
        sys.exit("Missing DEM files (fetch on a networked machine, or drop "
                 "--skip-fetch):\n  " + "\n  ".join(missing))
    tsm = float(cfg.get("target_support_m", 1000.0))
    raw, rights, native, ref_ids = study.load_real_units(
        units, tsm, cfg.get("reproject", True))
    reference_id = ref_ids[-1]
    return raw, rights, native, reference_id, tsm


def _run_ablation(raw, rights, native, reference_id, tsm, out):
    """Run the decision under ALL FIVE lenses on ONE set of comparison inputs and
    report what each concludes. The 'best analog' is lens-dependent: core and the
    extended / geomorphic / landform / texture morphology axes can rank candidates
    differently, and a Pareto TIE under one lens may resolve under another -- so a
    single run surfaces the full tie-break rather than one lens's verdict. Prints a
    readable table, writes ablation.json, returns 0. Morphology screening only."""
    LENSES = ("core", "extended", "geomorphic", "landform", "texture")
    rows = []
    for lens in LENSES:
        pk = study.compare_units(raw, rights, native, reference_id=reference_id,
                                 target_support_m=tsm, decision_metrics=lens)
        fr = pk.get("frontier") or {}
        layer1 = (fr.get("pareto_layers") or [[]])[0]
        rows.append({"lens": lens, "result_state": pk["result_state"],
                     "recommended_unit": pk.get("recommended_unit"),
                     "pareto_layer1": layer1})

    print("")
    print("=" * 78)
    print("TerraTrace five-lens decision ablation -- SAME data, every decision lens")
    print("=" * 78)
    print(f"reference_id = {reference_id}    target_support_m = {tsm:g} m")
    print(f"{'lens':<11} {'result_state':<22} {'recommended_unit':<18} pareto_layer1")
    print("-" * 78)
    for r in rows:
        layer = "{" + ", ".join(str(u) for u in r["pareto_layer1"]) + "}"
        print(f"{r['lens']:<11} {str(r['result_state']):<22} "
              f"{str(r['recommended_unit']):<18} {layer}")
    print("-" * 78)

    os.makedirs(out, exist_ok=True)
    payload = {"reference_id": reference_id, "target_support_m": tsm, "lenses": rows}
    path = os.path.join(out, "ablation.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    print(f"[ablation] wrote {path}")
    print(HONEST_NOTE)
    return 0


def _print_headline(package, conf, manifest, out):
    """Print the one-screen result summary (honest, no composite score)."""
    phash = package.get("package_hash") or ""
    profile = package.get("profile") or {}
    print("")
    print("=" * 68)
    print("TerraTrace multi-body analog study -- RESULT")
    print("=" * 68)
    print(f"source_label     = {profile.get('source_label')}")
    print(f"result_state     = {package.get('result_state')}")
    print(f"recommended_unit = {package.get('recommended_unit')}")
    print(f"package_hash     = {phash[:16]}...")
    print(f"confidence       = {str(conf.get('verdict', '')).upper()} -- {conf.get('rationale', '')}")
    sig = package.get("significance") or {}
    if "recommendation_significant" in sig:
        print(f"significance     = recommendation_significant={sig['recommendation_significant']} "
              f"(runner_up={sig.get('runner_up')})")
    files = ", ".join(sorted(manifest.get("files", {})))
    print(f"bundle           = {out}")
    print(f"                   [{files}, confidence.json]")
    print(HONEST_NOTE)


def _finish(package, out):
    """All modes converge here: compute decision confidence, export the full
    bundle, write confidence.json alongside it, print the headline. Return 0."""
    conf = confidence.decision_confidence(package)
    os.makedirs(out, exist_ok=True)
    manifest = bundle.export_bundle(package, out)
    with open(os.path.join(out, "confidence.json"), "w", encoding="utf-8") as fh:
        json.dump(conf, fh, indent=2, sort_keys=True)
    _print_headline(package, conf, manifest, out)
    return 0


def run_from_config(cfg, out="artifacts/real_study", dry_run=False,
                    synthetic=False, skip_fetch=False,
                    decision_metrics=None, ablation=False):
    """Drive the whole pipeline from an already-parsed config DICT.

    Factored out of main() with NO YAML/file I/O so the orchestration is
    unit-testable offline without PyYAML. Returns an exit code (0 = clean;
    --dry-run returns 0/2). REAL mode may sys.exit on a missing key / DEM.

    ablation=True obtains the comparison inputs ONCE (synthetic surfaces, or real
    DEMs via load_real_units) and runs the decision under all five lenses instead
    of a single study -- see _run_ablation. decision_metrics (when not None)
    overrides cfg["decision_metrics"] for the single-study path ONLY, applied to a
    shallow copy so the caller's config is never mutated.
    """
    if dry_run:
        return _dry_run(cfg)
    if ablation:
        if synthetic:
            print("[mode] synthetic ablation (deterministic offline surfaces)")
            raw, rights, reference_id, tsm = _synthetic_inputs(cfg)
            native = tsm
        else:
            print("[mode] real ablation (download + rasterio)")
            raw, rights, native, reference_id, tsm = _real_inputs(cfg, skip_fetch)
        return _run_ablation(raw, rights, native, reference_id, tsm, out)
    if decision_metrics is not None:
        cfg = dict(cfg, decision_metrics=decision_metrics)
    if synthetic:
        print("[mode] synthetic (deterministic offline surfaces)")
        package = _synthetic_package(cfg)
    else:
        print("[mode] real (download + rasterio)")
        package = _real_package(cfg, skip_fetch)
    return _finish(package, out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="One-command real multi-body analog study for TerraTrace "
                    "(morphology screening only).")
    ap.add_argument("--config", required=True, help="AOI config YAML (see config/real_multibody.example.yml)")
    ap.add_argument("--out", default="artifacts/real_study", help="output bundle directory")
    ap.add_argument("--dry-run", action="store_true",
                    help="preflight only (offline); no fetch, no DEM reads; exit 0/2")
    ap.add_argument("--synthetic", action="store_true",
                    help="deterministic offline surfaces (no fetch, no rasterio)")
    ap.add_argument("--skip-fetch", action="store_true",
                    help="REAL mode: assume DEMs are already on disk; do not download")
    ap.add_argument("--decision-metrics",
                    choices=("core", "extended", "geomorphic", "landform", "texture"),
                    default=None,
                    help="override the config's decision lens for the single study "
                         "(ignored under --ablation, which runs all five)")
    ap.add_argument("--ablation", action="store_true",
                    help="run the decision under ALL FIVE lenses (core/extended/"
                         "geomorphic/landform/texture) on ONE dataset; print a table and "
                         "write ablation.json instead of a single study bundle")
    args = ap.parse_args(argv)
    cfg = _load_config(args.config)
    return run_from_config(cfg, out=args.out, dry_run=args.dry_run,
                           synthetic=args.synthetic, skip_fetch=args.skip_fetch,
                           decision_metrics=args.decision_metrics,
                           ablation=args.ablation)


if __name__ == "__main__":
    raise SystemExit(main())




