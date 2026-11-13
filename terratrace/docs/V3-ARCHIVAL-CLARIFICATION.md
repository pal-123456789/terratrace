# V3 archival clarification

**Why this page exists.** The v3 benchmark is described as *pre-specified but not fully
pre-registered*. Three things about it are easy to misread from the repository alone: a stale
header inside the frozen config, a config checksum that does not match the file shipped at
HEAD, and the fact that the confirmatory experiment uses one decision lens rather than all six.
This page records each one from git, so no reader has to reconstruct it, and so no future
edit can quietly "tidy" the record.

Nothing in this page changes a result. Every number below is either read out of the committed
artifacts or recovered from git history.

## 1. The stale header in the frozen config

`config/matched_footprint_v3.yml` opens with, verbatim:

```
# TerraTrace matched-footprint benchmark -- v3 REFERENCE PANEL
#
# PROPOSED 2026-11-05. NOT YET FROZEN -- see docs/BENCHMARK-PROTOCOL-v3.md.
```

**`NOT YET FROZEN` is stale and wrong, and it is left exactly as it was written.** It was true
when the file was drafted: the author wrote the panel before any v3 data existed and marked it
as a proposal pending freeze. The file was then never edited again — it was used as written.
The header was simply not revised once the run had happened.

It is deliberately **not** corrected here. Editing any byte of that file would change the
checksum that the results page publishes, which is the very thing a reproducer checks first;
and the project's own rule for that file is *"do not edit expectations after seeing results;
any change must be a NEW versioned file with the reason recorded."* Correcting a comment to
make the file look tidier would violate the rule it states. The correct fix is this page.

## 2. The actual chronology

Recovered from git; all times IST.

| when | what | evidence |
|---|---|---|
| 2026-10-16 19:33 | The v3 rules committed — the resolution-change classifier, the panel runner, the two smooth non-volcanic controls | `60c7d63` |
| 2026-11-05 ~19:55 | The v3 config written — 708 s before the result bundle, per the bundle's own provenance block | `config/matched_footprint_v3.yml` in `820c17d` |
| 2026-11-05 20:06:54 | **The benchmark run.** Result bundle written. | `artifacts/mf_panel_v3/matched_panel_v3_real.json` |
| 2026-11-06 10:20 | The result bundle, the results page **and the protocol document** first appear in git, in one commit | `820c17d` |
| 2026-11-06 10:29 | One comment in the config corrected (Nevada Basin σ), protocol updated to match | `ddb2247` |

The load-bearing line is the fourth. **The rules and the config existed before the data; the
protocol document did not.** It was committed in the same commit as the results, fourteen hours
after the run. That is the entire reason v3 is not called fully pre-registered.

## 3. Pre-specified is not the same as pre-registered

> **The v3 evaluation was pre-specified: the configuration and decision rules preceded the data
> run. The protocol document itself was committed after the run, so we do not describe the
> experiment as fully pre-registered.**

The distinction is not a technicality. Pre-registration means a third party could have checked
the protocol text *before* the data existed. For v3 nobody could, because the text appears in
git only alongside the result. What *is* verifiable, and is the honest claim, is that the
decision rules (`panel_v3.py`, `confirmation.py`, both committed 2026-10-16, three weeks earlier)
and the config were fixed before any v3 data was read, and were not modified afterwards.

We do not strengthen this. Wherever the S/V/R verdicts appear, the caveat appears with them —
enforced mechanically, see §7.

## 4. Config identity: two checksums, one file

| revision | sha256 | what it is |
|---|---|---|
| at the result commit `820c17d` | `70eeafd4160f11502a35c898dfc47daef4f7087dd311adbd9a8c9c2aa236de4f` | **the config that produced the result** |
| shipped at HEAD | `985350769cc7d347a4d524b11cd47da04b3e36948e1eff7f40e3eaccbd324f0c` | the same file after one comment was corrected |

The two differ in exactly one line, and it is a comment:

```diff
-  earth_nevada_basin: other           # sigma ~244 m -- basin-and-range, near-miss
+  earth_nevada_basin: other           # sigma ~562 m -- basin-and-range, near-miss
```

The parameter hash — the parsed YAML with comments stripped, dumped canonically — is
`88c4386da861be286d19c2aec13cf7c9597fe2586a78210bf28d84c008a01238` for **both** revisions. Every
analytical parameter is byte-identical. The corrected comment is the σ annotation of the
near-miss candidate, changed from a figure taken from secondary literature (~244 m) to the
value the study itself measured (562 m). It is an annotation of a candidate that is neither a
control nor a winner; it affects no axis, no support, and no verdict.

The results page previously said the config was "unmodified since". That was true when written
and was falsified nine minutes later by `ddb2247`; it is corrected there, and the correction is
asserted by a test rather than trusted (see §7).

## 5. Scope: one lens, not six

The confirmatory S/V/R verdicts were produced with `decision_metrics="core"` — the **core
decision lens**. The bundle records this itself (`"decision_metrics": "core"`), so it is
checkable from the artifact and not only from prose.

> The v3 confirmatory S/V/R experiment uses the core decision lens. TerraTrace supports
> additional analytical lenses, but these are not independent scientific replications of the
> v3 finding.

The engine ships five default lenses and an opt-in hydro lens, and they remain available for
exploration. They re-examine the same terrains through different axis sets; they are not
independent datasets, independent sites, or independent experiments, and no result here is
claimed to have been replicated across them.

## 6. What is published, and what has to be fetched

| item | status |
|---|---|
| The v3 result bundle (1.1 MB JSON) | **committed** — `artifacts/mf_panel_v3/matched_panel_v3_real.json`, sha256 `4a4922e3…` |
| The config, the rules, the protocol, the results page | committed |
| The DEMs the run consumed | **not committed** — fetched from public sources; the exact commands and per-file checksums are in the source lock and the reproducibility page |
| The synthetic canonical study | committed under `artifacts/` |

Until recently the result bundle itself was git-ignored: the results page published a checksum
for a file no reader could obtain, and the benchmark could only be checked by re-running it in
full. That was the same defect class as citing a document that exists on one machine — a claim
whose evidence is not in the repository. It is committed now. No published number changed.

## 7. How each claim here is checked

`tests/test_v3_archival.py` asserts, on every run and in CI:

- the committed bundle's sha256 equals the value the results page publishes;
- the bundle is **tracked by git**, not merely present on disk;
- the six classification counts sum to the number of confirmatory cells (15), and all six
  categories exist as keys, so a category cannot be dropped by omission;
- the breakdown printed in `RESULTS-v3.md` equals the counts in the artifact;
- **no public surface states a breakdown that does not sum to 15, and none omits a non-zero
  category** — the arithmetic guard for the class of error this page was written to close;
- the v3 config's parameter hash still equals the frozen value, so a future edit to any
  analytical parameter fails the build;
- every surface that quotes the v3 verdicts also carries the pre-specification caveat.

Reproduce any of it by hand:

```bash
git show 820c17d:terratrace/config/matched_footprint_v3.yml | sha256sum
sha256sum terratrace/artifacts/mf_panel_v3/matched_panel_v3_real.json
python -c "import json;d=json.load(open('terratrace/artifacts/mf_panel_v3/matched_panel_v3_real.json'));print(d['hypotheses']['R']['counts'])"
```

## 8. What this page does not claim

It does not claim that v3 is pre-registered, that the lenses replicate one another, that the
config is byte-identical (it is not — one comment differs), or that any of this has been
examined by an external reviewer. It is an internally prepared record of an internal audit.
