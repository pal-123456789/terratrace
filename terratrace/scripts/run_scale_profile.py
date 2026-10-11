#!/usr/bin/env python3
"""TerraTrace SCALE-RESOLVED analog profile -- one command, one scale sweep.

A single study answers "how similar is this terrain to the reference at ONE
common support?". This orchestrator answers the scale-resolved questions a single
study cannot: "at what spatial scales does candidate X resemble the reference, and
does the single best analog CHANGE with scale?". It sweeps a list of common
supports and, at each one, re-runs the proven comparison core
(terratrace.study.compare_units, core lens) and records every candidate's overall
core distance and Pareto layer -- so the output is a transparent per-scale
profile, NOT a composite likeness score, and it introduces NO new morphology math.

Three ways to run it, so the whole pipeline is exercisable OFFLINE and the REAL
download path stays one flag away on a networked machine:

  --dry-run    Preflight ONLY (offline): validate the config schema + every bbox,
               pick the catalog source that covers each AOI, print an approximate
               request size (at the finest support), exit 0 (clean) / 2 (problems).
  --synthetic  Deterministic OFFLINE surfaces (no fetch, no rasterio): one tilted
               plane + per-unit seeded roughness per unit, swept through the SAME
               engine, so scale_profile.json/.md are produced and testable offline.
  (default)    REAL mode: preflight, fetch any missing candidate DEMs from
               OpenTopography (needs OPENTOPO_API_KEY + rasterio; planetary
               reference DEMs must already be on disk), then load every unit ONCE
               at the FINEST support and let compare_units re-aggregate each coarser
               support from those arrays.

Scientific boundary (claim firewall): map-scale terrain-MORPHOLOGY screening
resolved across spatial scales only -- no traversability, geologic-equivalence,
site-access, resource, or mission-readiness claim.

Pure standard library + the terratrace engine. PyYAML is imported LAZILY inside
_load_config only (the NumPy-only CI env has no yaml); rasterio is only touched on
the REAL path, via the engine, never under --dry-run / --synthetic.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from terratrace import multiscale, preflight, study, synthetic

DEFAULT_SUPPORTS = (1000.0, 1500.0, 2000.0, 3000.0, 4000.0)

HONEST_NOTE = (
    "NOTE: map-scale terrain-MORPHOLOGY screening resolved across spatial scales "
    "only -- a per-scale Pareto profile, NOT a composite likeness score, and no "
    "traversability, geologic-equivalence, site-access, or mission-readiness claim.")


def _load_config(path):
    """Parse the YAML config into a plain dict.

    PyYAML is imported LAZILY here (not at module top) so the engine's offline
    tests can drive run_from_config() with a plain dict without requiring PyYAML
    -- the NumPy-only CI env has no yaml (it ships in requirements-real).
    """
    import yaml
    with open(path, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _candidate_units(cfg):
    """The candidate unit list, accepting either the single-study ``earth_units``
    key or the atlas-style ``candidates`` key (whichever is present)."""
    return list(cfg.get("earth_units") or cfg.get("candidates") or [])


def _supports(cfg):
    """The ascending sweep of common supports (metres). Defaults to
    DEFAULT_SUPPORTS when the config omits a top-level ``supports`` list."""
    raw = cfg.get("supports") or list(DEFAULT_SUPPORTS)
    return sorted(float(s) for s in raw)


def _reference_id(units):
    """The reference unit id: the one flagged is_reference, else the first unit."""
    return next((u["id"] for u in units if u.get("is_reference")),
                units[0]["id"] if units else None)


def _print_preflight(report):
    """Human-readable preflight: per-unit ok/source/size, warnings, hard problems."""
    for uid, u in report["units"].items():
        rec = u.get("recommended_source") or {}
        est = u.get("estimates") or {}
        size = (f"~{est['download_mb']:.1f} MB, ~{est['pixels']:,} px" if est else "size n/a")
        print(f"  - {uid:28s} {'OK  ' if u['ok'] else 'FAIL'} "
              f"source={rec.get('source_id')} {size}")
        for w in u.get("warnings", []):
            print(f"      ! warning: {w}")
    if report["problems"]:
        print("[preflight] PROBLEMS:")
        for p in report["problems"]:
            print(f"      x {p}")
    else:
        print("[preflight] no hard problems.")


def _dry_run(cfg):
    """--dry-run: preflight every unit (offline). Return 0 (clean) / 2 (problems).

    Sizing uses the FINEST support (smallest = highest resolution = largest
    request), so the printed estimate is the conservative upper bound of the
    sweep. The config is normalised to the schema preflight understands
    (reference + earth_units) so a ``candidates``-key config preflights too.
    """
    supports = _supports(cfg)
    pf_cfg = {"target_support_m": min(supports),
              "min_valid_fraction": cfg.get("min_valid_fraction", 0.5),
              "reference": cfg.get("reference"),
              "earth_units": _candidate_units(cfg)}
    print(f"[preflight] scale sweep over supports "
          f"{', '.join(f'{s:g}' for s in supports)} m "
          f"(sizing at finest support {min(supports):g} m)")
    report = preflight.preflight_config(pf_cfg)
    _print_preflight(report)
    return 0 if report["ok"] else 2


def _synthetic_profile(cfg):
    """--synthetic: build one deterministic surface per unit (no fetch, no
    rasterio) and sweep it through multiscale.scale_profile.

    Surfaces are built at the FINEST support (native == min(supports)) so every
    requested support aggregates UP from a real native grid; each unit gets a
    gently tilted plane plus seeded roughness on a per-unit amplitude ladder (the
    reference and the first candidate share the smallest amplitude -> nearest
    realisation, each later candidate progressively rougher), so the candidates
    genuinely differ and the per-scale profile is a real ordering offline.
    """
    supports = _supports(cfg)
    native = min(supports)
    units = [cfg["reference"]] + _candidate_units(cfg)
    reference_id = _reference_id(units)
    raw, rights = {}, {}
    for i, u in enumerate(units):
        amp = 30.0 if i <= 1 else 30.0 + 25.0 * (i - 1)
        z = (synthetic.plane((80, 80), slope_x=0.02, dx=native)
             + synthetic.rough_field((80, 80), amp, seed=i))
        raw[u["id"]] = z
        rights[u["id"]] = u.get("rights_status", "verified_allowed")
    return multiscale.scale_profile(raw, rights, native, reference_id, supports,
                                    min_valid=cfg.get("min_valid_fraction", 0.5))


def _fetch_missing(cfg):
    """REAL mode: download any candidate DEM not already on disk (OpenTopography
    global DEM or USGS 3DEP via the same free key). The planetary reference DEM is
    NOT fetched here -- it must already exist (print the USGS instruction + abort
    if missing)."""
    from terratrace import ingest
    key = os.environ.get("OPENTOPO_API_KEY")
    if not key:
        sys.exit("Set OPENTOPO_API_KEY (free key: https://portal.opentopography.org).")
    ref = cfg["reference"]
    if not os.path.exists(ref["path"]):
        sys.exit(
            f"Reference DEM missing: {ref['path']} (id={ref.get('id')})\n"
            "  Planetary reference DEMs (e.g. Mars MGS MOLA 463m) are downloaded\n"
            "  once from USGS Astrogeology:\n"
            "    https://astrogeology.usgs.gov/search/map/mars_mgs_mola_dem_463m\n"
            "  save it to that path, then re-run.")
    for unit in _candidate_units(cfg):
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

def _real_profile(cfg, skip_fetch):
    """REAL mode: preflight (abort on hard problems), fetch missing candidate DEMs
    (unless --skip-fetch), then load EVERY unit ONCE at the FINEST support via
    study.load_real_units and sweep. compare_units re-aggregates each coarser
    support from those finest-support arrays, so one load serves the whole sweep.
    Requires rasterio."""
    supports = _supports(cfg)
    if _dry_run(cfg) != 0:
        sys.exit("[preflight] aborting: fix the problems above "
                 "(adjust bboxes / bodies / paths in the config) and re-run.")
    if not skip_fetch:
        _fetch_missing(cfg)
    units = [cfg["reference"]] + _candidate_units(cfg)
    missing = [u["path"] for u in units if not os.path.exists(u["path"])]
    if missing:
        sys.exit("Missing DEM files (fetch on a networked machine, or drop "
                 "--skip-fetch):\n  " + "\n  ".join(missing))
    finest = min(supports)
    raw, rights, native, ref_ids = study.load_real_units(
        units, finest, cfg.get("reproject", True))
    reference_id = ref_ids[-1] if ref_ids else _reference_id(units)
    return multiscale.scale_profile(raw, rights, native, reference_id, supports,
                                    min_valid=cfg.get("min_valid_fraction", 0.5))


def _fmt_dist(d):
    """Format a core distance, rendering NaN (an ineligible candidate) as n/a."""
    return f"{d:.4f}" if isinstance(d, (int, float)) and d == d else "n/a"

def render_scale_profile_md(profile, signature):
    """Render the profile as Markdown: a title + firewall line, a support x
    (best analog + per-candidate core distance) table, a per-candidate layer-1
    analog-band table, and the verbatim honest note."""
    supports = profile["supports"]
    cands = profile["candidates"]
    best = profile["best_by_support"]
    L = ["# TerraTrace Scale-Resolved Analog Profile", ""]
    L.append(f"_{HONEST_NOTE}_")
    L.append("")
    L.append(f"- reference: `{profile['reference_id']}`")
    L.append(f"- candidates: {', '.join(cands) if cands else '(none)'}")
    L.append(f"- supports swept (m): {', '.join(f'{s:g}' for s in supports)}")
    L.append(f"- single best analog scale-stable across supports: "
             f"{'yes' if signature['scale_stable'] else 'no'}")
    L.append("")
    L.append("## Core distance + best analog by support")
    L.append("")
    L.append("Each cell is a candidate's OVERALL core distance (L2 norm of its "
             "slope / relief / ruggedness / connectivity distance vector) to the "
             "reference at that support; `n/a` marks an ineligible candidate. "
             "`best analog` is the lone Pareto recommendation (`TIE/none` where "
             "the engine reaches no single recommendation).")
    L.append("")
    L.append("| support (m) | best analog | " + " | ".join(cands) + " |")
    L.append("|---:|:--|" + "".join("---:|" for _ in cands))
    for i, s in enumerate(supports):
        row = [f"{s:g}", str(best[i]) if best[i] is not None else "TIE/none"]
        row += [_fmt_dist(profile["per_candidate"][c]["distance"][i]) for c in cands]
        L.append("| " + " | ".join(row) + " |")
    L.append("")
    L.append("## Per-candidate layer-1 analog band")
    L.append("")
    L.append("`fraction_layer1` is how often a candidate is Pareto non-dominated "
             "across the swept supports; `band` is the (min, max) support span over "
             "which it is non-dominated.")
    L.append("")
    L.append("| candidate | fraction_layer1 | layer-1 band (m) |")
    L.append("|:--|---:|:--|")
    for c in cands:
        pc = signature["per_candidate"][c]
        band = pc["band"]
        band_s = f"{band[0]:g}..{band[1]:g}" if band else "(never layer 1)"
        L.append(f"| {c} | {pc['fraction_layer1'] * 100:.0f}% | {band_s} |")
    L.append("")
    L.append("## Note")
    L.append("")
    L.append(f"> {HONEST_NOTE}")
    L.append("")
    return "\n".join(L)

def _print_summary(profile, signature, out):
    """Print the one-screen scale-resolved profile (honest, no composite score)."""
    supports = profile["supports"]
    cands = profile["candidates"]
    best = profile["best_by_support"]
    print("")
    print("=" * 78)
    print("TerraTrace scale-resolved analog profile")
    print("=" * 78)
    print(f"reference = {profile['reference_id']}   candidates = {len(cands)}   "
          f"supports = {', '.join(f'{s:g}' for s in supports)} m")
    print(f"single best analog scale-stable across supports: "
          f"{'YES' if signature['scale_stable'] else 'NO'}")
    head = f"{'support(m)':>11}  {'best analog':<20}" + "".join(f"{c[:16]:>17}" for c in cands)
    print(head)
    print("-" * len(head))
    for i, s in enumerate(supports):
        b = str(best[i]) if best[i] is not None else "TIE/none"
        line = f"{s:>11g}  {b:<20}" + "".join(
            f"{_fmt_dist(profile['per_candidate'][c]['distance'][i]):>17}" for c in cands)
        print(line)
    print("-" * len(head))
    for c in cands:
        pc = signature["per_candidate"][c]
        band = pc["band"]
        band_s = f"{band[0]:g}..{band[1]:g} m" if band else "(never layer 1)"
        print(f"  {c:<26} layer1 {pc['fraction_layer1'] * 100:>3.0f}%   band {band_s}")
    print(f"bundle = {out}  [scale_profile.json, scale_profile.md]")


def _finish(profile, out):
    """Write scale_profile.json (profile + signature + note) + scale_profile.md,
    print the summary + the honest note. Return 0."""
    os.makedirs(out, exist_ok=True)
    signature = multiscale.scale_profile_signature(profile)
    payload = {"profile": profile, "signature": signature, "note": HONEST_NOTE}
    with open(os.path.join(out, "scale_profile.json"), "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, sort_keys=True)
    with open(os.path.join(out, "scale_profile.md"), "w", encoding="utf-8") as fh:
        fh.write(render_scale_profile_md(profile, signature))
    _print_summary(profile, signature, out)
    print(HONEST_NOTE)
    return 0

def run_from_config(cfg, out="artifacts/scale_profile", dry_run=False,
                    synthetic=False, skip_fetch=False):
    """Drive the whole scale sweep from an already-parsed config DICT.

    Factored out of main() with NO YAML/file I/O so the orchestration is
    unit-testable offline without PyYAML. Returns an exit code (0 = clean;
    --dry-run returns 0/2). REAL mode may sys.exit on a missing key / DEM.
    """
    if dry_run:
        return _dry_run(cfg)
    if synthetic:
        print("[mode] synthetic (deterministic offline surfaces)")
        profile = _synthetic_profile(cfg)
    else:
        print("[mode] real (download + rasterio)")
        profile = _real_profile(cfg, skip_fetch)
    return _finish(profile, out)


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="TerraTrace scale-resolved analog profile: sweep a list of "
                    "common supports and report how each candidate's morphology "
                    "distance + Pareto rank change with scale (morphology "
                    "screening only).")
    ap.add_argument("--config", required=True,
                    help="scale-profile config YAML (see config/scale_profile.example.yml)")
    ap.add_argument("--out", default="artifacts/scale_profile",
                    help="output directory for scale_profile.json + scale_profile.md")
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
