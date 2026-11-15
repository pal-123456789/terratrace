# The independent-axis probe — what the declared axes cannot see, and whether it matters

**Status: EXPLORATORY SENSITIVITY PROBE.** It runs on the 18 cells of the already-published lunar
panel v2. It does not modify that panel, its protocol, its artifact or its numbers; it is **not a
pre-registration** and no result here is confirmatory, because the same cells were examined in v2
before this probe existed. The protocol was frozen before the recorded run at
`config/lunar_axis_probe_v1.yml`; the record is
`artifacts/lunar_axis_probe/lunar_axis_probe.json`.

**Why this exists.** The lunar half of the project has one limitation that everything else follows
from: its three declared axes — mean slope, mean 3×3 relief, elevation σ — span **a single
dimension** (`docs/LUNAR-DEMONSTRATION.md`, `artifacts/dependence/dependence_audit.json`). Three
descriptors that are three names for roughness amplitude cannot separate a surface that is rough from
one that is *differently* rough. So the probe asked the two questions that actually decide whether
that matters:

> **One term, defined once.** Throughout this page a descriptor is called **non-redundant** when the
> three declared axes do not predict it — a measured statement about *this* panel's axes and *this*
> dataset, quantified by adjusted R². It is **not** a claim that anything here independently confirms
> anything: the probe reuses the engine's own descriptors and the panel's own cells, so it is
> correlated with them by construction and can neither corroborate nor contradict them from outside.
> "Independent" is never used in that validating sense on this page.

1. Is there a descriptor in the engine's own bank that carries information the three axes do not?
2. Would adding it change the decision?

Question 2 is the one that gets skipped, and it is the one that can embarrass a conclusion. The
answer turned out to be a negative result that is worth more than a fourth axis would have been.

## 1. The analytic half: what the three axes cannot see, as a matter of proof

The plane family `z = g·(x·cosθ + y·sinθ)` has one free parameter — azimuth θ — and if the three axes
are invariant under a transformation of it, they are provably blind to that dimension. Measured at
machine precision over eight azimuths:

| Operation on θ | max \|Δ mean slope\| | max \|Δ mean 3×3 relief\| | max \|Δ elevation σ\| | |
|---|---|---|---|---|
| θ → θ + 90° | 3.6e-15 | 1.1e-13 | 1.1e-13 | **invariant** |
| θ → 90° − θ | 7.1e-15 | 5.7e-14 | 2.3e-13 | **invariant** |
| θ → θ + 180° | 3.6e-15 | 5.7e-14 | 2.3e-13 | **invariant** |
| θ → θ + 45° | 7.1e-15 | **1.243e+02** | 1.1e-13 | not invariant |

Mean slope and elevation σ cannot depend on azimuth at fixed gradient magnitude, and mean 3×3 relief
depends on it only through the bounded symmetric factor ρ(θ) = |cos θ| + |sin θ| from the dependence
audit — which is invariant under a quarter turn and under reflection about the diagonal, and *not*
under a 45° rotation.

**Consequence.** The three declared axes are **exactly blind to a quarter-turn rotation of a planar
surface**. The fourth row matters as much as the first three: the axes are *not* blind to orientation
in general, only to that subgroup, so the claim is narrow and is stated narrowly.

The narrowness is the point. It says a specific family of descriptors *must* carry information the
three axes do not — those not invariant under a quarter turn — and it makes that a prediction rather
than a fishing expedition.

**How large is that family, measured?** Of the 180 bank scalars that can be computed on a plane,
**48 are not quarter-turn invariant** (relative tolerance 1e-9, over three azimuth pairs). They are
the curvature family, the *spread* statistics of ruggedness and slope, the spectral band roughnesses,
and the anisotropy, convergence and openness-difference families. The remaining 132 are as blind to
the quarter turn as the declared axes are, so this symmetry argument cannot even in principle point
at them.

**And the symmetry-predicted set is not the set the measurement finds — which is worth stating
plainly rather than glossing.** `variogram/nugget`, the descriptor that turns out to be the most
statistically independent on real terrain, *is* quarter-turn invariant and therefore invisible to
the argument above. Conversely `anisotropy/orientation_deg` *is* predicted by it and is inadmissible
(circular). So the analytic half establishes a genuine blindness of the declared axes and bounds one
family of candidates; it does not identify the best one. The measurement in §2 does that, and the two
disagree — which is the normal relationship between a symmetry argument and an experiment.

## 2. The measurement: which descriptors actually carry new information

Every admissible bank scalar was regressed, per cell, on the three declared axes over that cell's
eight units (the reference plus the seven Earth candidates — the frontier's own pool), and the fit
scored by **adjusted R²**.

Adjusted, because with n = 8 and p = 3 a **raw** R² has a chance level of p/(n−1) = **0.4286**. A raw
threshold of "below 0.5" would sit barely above pure noise. Adjusted R² has expectation ≈0 under the
null, which makes the cut-off mean something.

184 bank entries → **142 admissible** (a descriptor must vary across the compared units by at least 10 % of
its own mean in at least 16 of the 18 cells; 42 descriptors failed that, and 59 cell-level
comparisons were excluded for an undefined spread) → **141 decision-tested** (one excluded as
circular, below).

**Controls, both required to pass before any ranking is readable.** Two bank scalars are the *same
statistic* the declared axes compute, reached through the bank: `slope/mean` and
`iwahashi_pike/slope_mean`. Both came out at **adjusted R² = 1.000000 exactly** — the estimator
recovers perfect redundancy where it must exist.

Two more are *different estimators of the same idea*, and their values are informative in their own
right rather than being controls:

| Bank scalar | What it estimates | Adjusted R² on the three axes |
|---|---|---|
| `relief/mean` | relief over a **5×5** window, against the declared axis's 3×3 | 0.99967 |
| `roughness_length/rms_slope` | **RMS** of the gradient magnitude, against the mean of its arctangent | 0.99991 |

So a differently-windowed relief is 99.97 % determined by the three declared axes. That is a further,
independent reading of how one-dimensional this panel is, measured rather than asserted.

**The most independent admissible descriptor is `variogram/nugget`**: median adjusted R² **−0.511**,
median raw R² **0.136** — *below* the 0.4286 chance level. The three declared axes predict it **no
better than three random numbers would**. Physically that is sensible: the nugget is the
short-range variance left after spatial structure is accounted for, so it measures fine-scale
*incoherence* rather than amplitude, and amplitude is all the three axes know about.

Two descriptors rank near it: `tpi_landform/composition/upper_slope` (−0.258) and
`geomorphons/composition/ridge` (−0.191). `anisotropy/orientation_deg` ranks second at −0.262 and is
**excluded**: it is a circular quantity measured in degrees, where 359° and 1° are adjacent but
numerically far, so a Euclidean Pareto distance on it is meaningless. It is reportable as a finding
and is not admissible as an axis.

## 3. The consequence, and the control that decides how to read it

Adding a coordinate to a Pareto comparison can only ever **promote** a co-winner — dominance becomes
harder, never easier. A removal is therefore a machinery failure, not a finding, and the driver
refuses to publish if one occurs. On this record, none did.

Adding each candidate as a fourth axis, with distance measured from the reference and normalised by
the within-cell range:

| Added axis | Cells whose layer-1 set changes (of 18) |
|---|---|
| `variogram/nugget` | **0** |
| `geomorphons/composition/ridge` | 10 |
| `multiscale_tpi/composition/upper_slope` | 14 |
| `tpi_landform/composition/lower_slope` | 14 |
| `tpi_landform/composition/upper_slope` | 15 |
| `curvature_classes/composition/planar` | 15 |
| `iwahashi_pike/composition/6` | 16 |
| `iwahashi_pike/composition/4` | 17 |

Read alone, that table says the lunar frontier is fragile. **It says nothing of the kind, and the
control is what shows why.** The same test run against a **uniformly random** fourth coordinate, 300
draws:

| | |
|---|---|
| mean cells changed | **15.90** of 18 |
| median | 18 |
| 5th–95th percentile | 0 – 18 |
| fraction of draws changing ≥10 cells | 0.84 |
| fraction of draws leaving the frontier intact | 0.12 |

An arbitrary coordinate — one carrying no information whatsoever — moves the frontier in nearly
sixteen of eighteen cells. Across 141 candidate axes, **not one** exceeds the control's 95th
percentile. Every "finding" in the table above is the expected behaviour of adding a dimension to a
Pareto rule over eight points in three dimensions.

And the descriptor that is *most* independent by the measurement — the nugget, at −0.511 adjusted R²
— changes the decision at **zero** of the eighteen cells. Being statistically independent of the
declared axes and being decision-relevant are different properties, and this panel separates them.

## 4. What this establishes, and what it does not

**Established.**

- The three declared axes are exactly blind to a quarter-turn rotation of a planar surface
  (machine-precision, both directions).
- A genuinely non-redundant axis exists in the engine's own bank: `variogram/nugget` is predicted by
  the three axes no better than chance.
- The lunar panel's **sole-non-dominated** property is **fragile to the number of axes**, not to any
  particular axis. It is a property of running a Pareto rule over eight units in three dimensions.
- Independence and decision-relevance come apart: the most non-redundant axis found moves nothing.

**Not established, and this is the part to keep.**

- **This does not show that the declared axes are the wrong axes.** It shows that the frontier is
  decided by a near-degenerate coordinate.
- **This does not promote any Earth candidate.** Adding dimensions promotes co-winners without
  discriminating between them; the probe bounds a *claim*, not a candidate.
- The panel's published ranking stands as published — **provisional and relative**, which is how it is
  already labelled. What this adds is a measurement of exactly how provisional: the sole-winner
  property should not be read as evidence about candidates at all.

**A defect found in the engine by this probe, reported because it is not this probe's — since fixed.**
The panel normalises each axis by dividing by the **reference** value, which is undefined when that
value is 0. **13 of the 184** bank scalars hit an undefined normalisation, and they split into two
causes that are not the same defect: **12** because a compositional fraction can be zero for a
reference window (`geomorphons/composition/flat` and `/pit` are 0 in all 18 cells), and **1** because an
input is non-finite — the cause the first version of this audit could not see, since a NaN candidate
turned the distance into a NaN rather than into the `None` the audit tested for. The three declared axes
are strictly positive, so the published panel is untouched by either.

What changed is that the undefined case is no longer *silent*. The engine's policy now lives in
`decision.axial_fractional_distance`: an exact both-zero agreement is a distance of 0.0, and a zero
reference against a non-zero value **refuses** with `UndefinedNormalisation`, as does any non-finite
input. The refusal is not stylistic — `decision.non_dominated` excludes any unit carrying a non-finite
distance, so the old NaN did not fail, it quietly compared fewer units and returned a ranking over
them. The probe still works around the normalisation with a within-cell **range** for its own added
axis, and still records which descriptors cannot be normalised the engine's way rather than reusing it.

**One number in the frozen protocol disagrees with the run, and it is left standing.** The pre-run
rationale in `config/lunar_axis_probe_v1.yml` says the NaN audit "shows 13 of the 184 bank descriptors
hit exactly that" — the zero-reference case. The run recorded **12** for that case, so the protocol's
number was wrong when it was written, before any of this changed. The total is 13 **now**, but for a
different reason: 12 zero-reference plus 1 non-finite input. The protocol is deliberately **not**
edited. It is the record of what was declared before the run, and rewriting it to agree with a later
result would destroy the one thing that makes a frozen protocol worth having. The disagreement is
recorded here instead, where a reader comparing the two will find it.

## 5. Reproducing it

```
cd terratrace
python3 scripts/lunar_axis_probe.py      # ~40 s with the destination-grid cache warm
python3 -m pytest tests/test_axis_probe.py    # or: python3 tests/run_tests.py
```

The driver **refuses to run** unless it first reproduces the v2 artifact's layer-1 sets at all 18
cells — a probe that cannot reproduce the panel it attacks is attacking something else — and
**refuses to publish** if a Pareto removal is detected anywhere, because dominance makes that
impossible and it is how a NaN in an added coordinate would show up.
