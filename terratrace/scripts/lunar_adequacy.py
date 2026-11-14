"""The lunar panel's THREE verdicts, separated: ranking, adequacy, and evidence sufficiency.

The v2 panel answers one question -- which Earth candidate is closest to each lunar reference, among
the seven tested -- and answers it decisively at all 18 site x support cells. It does not answer the
other two questions a reader will otherwise assume are covered:

* is any candidate actually INSIDE the reference's own morphological variability at this scale?
  (absolute adequacy, calibrated from held-out sub-windows of the reference itself);
* is the evidence enough to support either statement? (candidate count, support count, valid
  coverage, whether an adequacy band could be calibrated at all, how many error realisations were
  drawn, and whether the axes are independent dimensions).

`terratrace/verdicts.py` holds the composition and the rules; this script supplies the real numbers.
The RANKING half is read from the committed v2 artifact rather than recomputed, so the published
ordering is the one being reported and the two cannot drift apart.

Every unit is placed on the same exact destination grid the panel used -- `common_grid`, 9000 m,
500/750/1000 m cells, area-weighted -- so "the reference's own variability" is measured on exactly the
same ground as the comparison it is judging.

Output: `artifacts/lunar_adequacy/lunar_adequacy.json`.
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import lunar_sites_v2 as v2                                          # noqa: E402
from terratrace import adequacy, common_grid as cg, verdicts          # noqa: E402

OUT = ROOT / "artifacts" / "lunar_adequacy" / "lunar_adequacy.json"
V2_ARTIFACT = ROOT / "artifacts" / "lunar_sites_v2" / "lunar_sites_v2.json"
DEPENDENCE = ROOT / "artifacts" / "dependence" / "dependence_audit.json"

FOOTPRINT_M = cg.DEFAULT_FOOTPRINT_M
SUPPORTS = [500.0, 750.0, 1000.0]


def main():
    v2art = json.loads(V2_ARTIFACT.read_text(encoding="utf-8"))
    ens = v2art.get("ensemble") or {}
    n_realisations = ens.get("n_draws")
    eff_rank = None
    if DEPENDENCE.exists():
        dep = json.loads(DEPENDENCE.read_text(encoding="utf-8"))
        ranks = [blk["effective_rank_95"] for entry in dep["panel"].values()
                 for blk in entry["pools"].values()]
        eff_rank = max(ranks) if ranks else None

    results = {"provenance": {
        "what": "the lunar panel's three verdicts, reported separately",
        "status": "CORRECTED EXPLORATORY REANALYSIS -- same data as the v2 panel",
        "not": "not confirmation and not a new pre-registration",
        "ranking_source": "artifacts/lunar_sites_v2/lunar_sites_v2.json (read, not recomputed)",
        "adequacy_method": "terratrace.adequacy -- the reference's own held-out 3x3 sub-window "
                           "self-distance band at the 95th percentile, calibrated for 'slope' and "
                           "'relief'; a candidate is adequate when its distance-to-reference is "
                           "inside the band on EVERY descriptor whose band could be established",
        "grid": "common_grid, 9000 m footprint, exact 500/750/1000 m cells, area-weighted",
        "score_firewall": "no composite score, here or anywhere; ranking is Pareto dominance and "
                          "adequacy is a band membership, and neither is derived from the other",
    }, "cells": {}}

    for support in SUPPORTS:
        key = f"{int(support)}m"
        n = cg.plan(FOOTPRINT_M, support)
        units, valid = {}, {}
        for sid, _name in v2.SITES:
            surf = v2.MOON / f"{sid}_surf.tif"
            if not surf.exists():
                continue
            lat, lon = v2.moon_centre(surf)
            z, rec = cg.read_exact(surf, lat, lon, "moon", support, n)
            units[f"LUNAR_{sid}"] = z
            valid[f"LUNAR_{sid}"] = rec["valid_fraction"]
        for uid, _where, fname, lon, lat in v2.CANDIDATES:
            z, rec = cg.read_exact(v2.EARTH / fname, lat, lon, "earth", support, n,
                                   source_posting_m=v2.EARTH_POSTING_M)
            units[uid] = z
            valid[uid] = rec["valid_fraction"]
        min_valid = min(valid.values())

        published = v2art["scales"][key]
        candidate_ids = [uid for uid, _w, _f, _lo, _la in v2.CANDIDATES]
        for sid, sname in v2.SITES:
            ref = f"LUNAR_{sid}"
            if ref not in units:
                continue
            # TWO comparisons, deliberately kept apart. The candidate pool is the reference plus
            # the seven Earth candidates -- the sibling lunar sites are NOT candidates of each
            # other, and letting them in would make the adequacy statement about a different field.
            sibs = [s for s in (f"LUNAR_{x}" for x, _n in v2.SITES) if s != ref and s in units]
            cand_units = {ref: units[ref]}
            cand_units.update({c: units[c] for c in candidate_ids})
            ctrl_units = {ref: units[ref]}
            ctrl_units.update({s: units[s] for s in sibs})
            ass = adequacy.adequacy_assessment(cand_units, support, ref, FOOTPRINT_M, support,
                                               descriptors=("slope", "relief"))
            # The DISCRIMINATION control: the reference's own band, tested against terrain from
            # other lunar sites. These are different places by construction, so if the band admits
            # them it is not separating similar from dissimilar and must not be read as adequacy.
            ctrl = adequacy.adequacy_assessment(ctrl_units, support, ref, FOOTPRINT_M, support,
                                                descriptors=("slope", "relief")) \
                if ctrl_units else None
            thresholds = {d: b["band"]["p95"] for d, b in ass["per_descriptor"].items()
                          if b.get("established")}
            controls = []
            if ctrl:
                for s in sibs:
                    controls.append({d: ctrl["per_descriptor"][d]["candidates"][s]["distance"]
                                     for d in thresholds})
            disc = verdicts.band_discrimination(controls, thresholds)
            disc["control_units"] = sibs
            disc["control_distances"] = controls

            # Two diagnostics that keep the reader from having to guess WHY the band failed, and
            # one fact that is worth knowing on its own: per descriptor, how wide is the band next
            # to the largest distance actually observed, and which unit is nearest the reference.
            # Reported PER DESCRIPTOR -- never averaged into a single number, because that would be
            # the composite score this project refuses to produce.
            band_width, nearest = {}, {}
            for d, blk in ass["per_descriptor"].items():
                if not blk.get("established"):
                    continue
                allu = dict(blk["candidates"])
                for s in sibs:
                    allu[s] = {"distance": ctrl["per_descriptor"][d]["candidates"][s]["distance"]}
                cand_max = max((e["distance"] for k, e in allu.items() if k in candidate_ids),
                               default=float("nan"))
                p95 = blk["band"]["p95"]
                band_width[d] = {"band_p95": p95, "max_candidate_distance": float(cand_max),
                                 "band_over_max": (float(p95 / cand_max)
                                                   if cand_max and cand_max > 0 else None)}
                best = min(allu.items(), key=lambda kv: kv[1]["distance"])
                nearest[d] = {"unit": best[0], "distance": float(best[1]["distance"]),
                              "is_sibling_site": best[0] in sibs}

            layer1 = published[sid]["layer1"]
            rec_unit = layer1[0] if len(layer1) == 1 else None
            ranks = verdicts.ranking_verdict(
                "RECOMMEND_FOLLOW_UP" if rec_unit else ("TIE" if layer1 else "INDETERMINATE"),
                layer1, recommended_unit=rec_unit,
                worst_axis_distance=published[sid]["axis_distance_fraction"].get(rec_unit)
                if rec_unit else None)
            ade = verdicts.adequacy_verdict(ass, discrimination=disc)
            suf = verdicts.sufficiency_verdict(
                n_candidates=len(candidate_ids), n_supports=len(SUPPORTS),
                min_valid_fraction=min_valid, adequacy_band_established=bool(ass["established"]),
                effective_rank=eff_rank, n_realisations=n_realisations, ensemble_claim=True)
            # provisional = the ranking is reported, but not at the sufficiency it would need
            ranks["provisional"] = suf["state"] != "SUFFICIENT"
            results["cells"][f"{sid}@{key}"] = {
                "site": sid, "site_name": sname, "support_m": support, "cells_per_side": n,
                "valid_fraction_min": float(min_valid),
                "verdict": verdicts.three_part_verdict(ranks, ade, suf),
                "adequacy_detail": ass,
                "band_width_diagnostic": band_width,
                "nearest_unit_per_descriptor": nearest,
            }

    OUT.parent.mkdir(parents=True, exist_ok=True)

    # --- the aggregate facts, computed from the cells rather than asserted
    cells = list(results["cells"].values())
    nn_total = nn_sibling = 0
    for c in cells:
        for v in c["nearest_unit_per_descriptor"].values():
            nn_total += 1
            nn_sibling += bool(v["is_sibling_site"])
    results["summary"] = {
        "n_cells": len(cells),
        "ranking_definite": sum(1 for c in cells
                                if c["verdict"]["relative_ranking"]["recommended_unit"]),
        "adequacy_not_established": sum(1 for c in cells
                                        if c["verdict"]["absolute_adequacy"]["state"]
                                        == "NOT_ESTABLISHED"),
        "sufficiency_states": sorted({c["verdict"]["evidence_sufficiency"]["state"]
                                      for c in cells}),
        "nearest_unit_is_a_sibling_lunar_site": {"of": nn_total, "count": nn_sibling},
        "reading": ("The ranking is definite at every cell and the absolute question is answered at "
                    "none of them, which is the separation this module exists to make visible. The "
                    "third number is the uncomfortable one: at "
                    f"{nn_sibling} of {nn_total} site x descriptor statistics the unit nearest a "
                    "lunar reference is ANOTHER LUNAR SITE, not any of the seven Earth candidates. "
                    "So 'earth_nevada_basin is the closest EARTH candidate' is true and 'Nevada is "
                    "closest to the Moon' is false, and the panel's own caveat -- six nearby sites "
                    "may be similar to each other rather than the method being insensitive -- is "
                    "now measured rather than suspected."),
        "caveat_on_the_sibling_result": ("This is a statement about these two descriptors at these "
                                         "supports, not about the terrain in the abstract. Six "
                                         "sites on one body sharing a descriptor signature could "
                                         "mean the sites are alike, that the descriptors cannot "
                                         "separate bodies, or both; nothing in this panel "
                                         "distinguishes those, and body-transfer calibration is an "
                                         "open item."),
    }
    OUT.write_text(json.dumps(results, indent=2), encoding="utf-8")

    print("=" * 96)
    print("LUNAR PANEL -- THREE VERDICTS, SEPARATED")
    print("=" * 96)
    print(f"{'site':8s} {'sup':>5s} {'RANKING':22s} {'ADEQUACY':24s} {'SUFFICIENCY':12s}")
    print("-" * 96)
    for cell in results["cells"].values():
        v = cell["verdict"]
        r, a, s = v["relative_ranking"], v["absolute_adequacy"], v["evidence_sufficiency"]
        rank = f"{r['state']} [{r['recommended_unit'] or '-'}]"
        ade = a["state"] + (f" {a['adequate_candidates']}" if a["adequate_candidates"] else "")
        print(f"{cell['site']:8s} {int(cell['support_m']):5d} {rank:22s} {ade:24s} {s['state']:12s}")
    n_ade = sum(1 for c in results["cells"].values()
                if c["verdict"]["absolute_adequacy"]["state"] == "ESTABLISHED_ADEQUATE")
    n_band = sum(1 for c in results["cells"].values()
                 if c["verdict"]["absolute_adequacy"]["state"] != "NOT_ESTABLISHED")
    print("-" * 96)
    print(f"cells: {len(results['cells'])}")
    print(f"  ranking definite: {sum(1 for c in results['cells'].values() if c['verdict']['relative_ranking']['recommended_unit'])}")
    print(f"  adequacy NOT_ESTABLISHED: {sum(1 for c in results['cells'].values() if c['verdict']['absolute_adequacy']['state'] == 'NOT_ESTABLISHED')}")
    first = next(iter(results["cells"].values()))
    print("\n  why the band failed, one cell as the example "
          f"({first['site']} @ {int(first['support_m'])} m):")
    for d, bw in first["band_width_diagnostic"].items():
        print(f"    {d}: band p95 {bw['band_p95']:.2f} vs largest candidate distance "
              f"{bw['max_candidate_distance']:.3f}  -> band is {bw['band_over_max']:.0f}x wider")
    disc = first["verdict"]["absolute_adequacy"]["discrimination"]
    print(f"    controls admitted: {disc['admitted']}/{disc['controls']} "
          f"(sibling lunar sites) -> discriminates: {disc['discriminates']}")
    print("\n  nearest unit to each reference, PER DESCRIPTOR (never averaged):")
    for site in sorted({c["site"] for c in results["cells"].values()}):
        c = results["cells"][f"{site}@500m"]
        nn = c["nearest_unit_per_descriptor"]
        print(f"    {site}: " + "  ".join(
            f"{d}->{v['unit']}{' (sibling site)' if v['is_sibling_site'] else ''}"
            for d, v in nn.items()))
    reasons = sorted({r for c in results["cells"].values()
                      for r in c["verdict"]["evidence_sufficiency"]["reasons"]})
    print("\n  sufficiency reasons seen:")
    for r in reasons:
        print(f"    - {r}")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
