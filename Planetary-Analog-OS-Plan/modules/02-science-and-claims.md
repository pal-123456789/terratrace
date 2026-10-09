# 02 — Science and Claims

## Scientific posture

TerraTrace compares **map-scale morphology**, not planetary worlds. Any stronger claim requires additional observation, mechanical characterization, operational testing, and outcome evidence.

## Observable taxonomy

| Class | Examples | v0.1 status |
|---|---|---|
| Topographic morphology | slope, local relief, detrended ruggedness | scored if support-verified |
| Morphology connectivity | below-threshold cell connectivity, corridor structure | scored conditionally |
| Radiometric context | image texture, albedo proxies | contextual only unless matched product support is verified |
| Material/geology | mineralogy, regolith class, soil mechanics | not scored in v0.1 |
| Operational environment | access, season, safety, repeatability | metadata/eligibility only |
| Planetary physics | gravity, atmosphere, radiation, thermal cycling | explicit non-transferable ledger |
| Rover behavior | traversability, traction, SLAM, autonomy success | prohibited v0.1 claim |

## Resolution and support

Raster posting is not equivalent to effective spatial support. A feature is valid only if its physical window and source uncertainty support it.

For raster cell spacing \(p\), source uncertainty \(\sigma_z\), and physical analysis window \(w\), record:

\[
\mathcal{S} = (p, w, \sigma_z, \rho, q)
\]

where:

- \(p\) = native posting;
- \(w\) = physical window in metres;
- \(\sigma_z\) = vertical uncertainty or documented proxy;
- \(\rho\) = resampling/aggregation method;
- \(q\) = quality-mask policy.

A comparison is eligible only when both units have a declared common support \(\mathcal{S}^*\) and the feature’s scale is materially larger than unsupported noise.

## Terrain descriptors

### Directional slope

For a digital elevation field \(z(x,y)\),

\[
\nabla z = \left(\frac{\partial z}{\partial x}, \frac{\partial z}{\partial y}\right)
\]

and local slope angle is:

\[
\theta(x,y) = \arctan\left(\sqrt{z_x^2 + z_y^2}\right)
\]

The implementation must specify finite-difference kernel, projected units, edge behavior, nodata handling, and whether slope is percent or degrees.

### Local relief

For window \(W_w(x,y)\):

\[
R_w(x,y) = Q_{0.95}(z|W_w) - Q_{0.05}(z|W_w)
\]

Robust quantiles are preferred over max–min because one artifact should not dominate a unit. The window \(w\) is physical, not merely a pixel count.

### Detrended ruggedness

Fit a local low-order surface \(\hat z_w\) over \(W_w\), then:

\[
T_w(x,y) = \sqrt{\frac{1}{|W_w|}\sum_{i \in W_w}(z_i - \hat z_w_i)^2}
\]

This is a terrain statistic at a declared scale. It is not mechanical roughness, wheel slip, or obstacle severity.

### Low-slope connectivity

Let \(V(x,y)=1\) when \(\theta(x,y)\leq\theta_{max}\) and quality masks pass. Define connected components under an explicitly chosen neighborhood \(N\). Report:

\[
C_{\theta}(A) = \frac{\max_{k} |\operatorname{component}_k(V \cap A)|}{|A|}
\]

This is a map-scale morphology statistic. It is not a route guarantee.

## Distribution comparison

For feature distribution \(F_A\) and \(F_B\), report more than one distance:

- Wasserstein distance for magnitude/shape;
- Kolmogorov–Smirnov distance for distribution divergence;
- quantile difference vector;
- spatial-pattern or connectivity comparison where relevant.

A normalized morphology distance can be:

\[
d_r(A,B) = \frac{W_1(F_{A,r},F_{B,r})}{s_r + \epsilon}
\]

where \(s_r\) is a declared scale, such as pooled interquartile range, and \(\epsilon\) prevents division by zero. The normalization must be documented and sensitivity-tested.

Do not sum \(d_r\) into a universal score by default.

## Decision logic

Let \(E_i\) be eligibility for terrain unit \(i\):

\[
E_i = D_i \land S_i \land Q_i \land R_i
\]

where:

- \(D_i\) = required data exists;
- \(S_i\) = common effective support is valid;
- \(Q_i\) = quality/missingness policy passes;
- \(R_i\) = rights/publication status is not misrepresented.

Only eligible units enter comparison. Results are then a vector:

\[
\mathbf{m}_i = (d_{slope}, d_{relief}, d_{ruggedness}, d_{connectivity})
\]

Use Pareto dominance rather than forced scalarization. Unit \(A\) dominates \(B\) only if it is no worse on every declared metric and strictly better on at least one. If no unit dominates the others, show a Pareto set or tie.

## Pseudocode

```text
load source_lock
validate product IDs, terms, CRS, datum, support, quality masks
load one Mars unit and 2–3 bounded Earth units
for each unit:
    validate geometry and coverage
    convert to approved analysis frame
    aggregate/degrade to common effective support
    apply nodata and quality masks
    compute slope distribution
    compute relief distributions at declared windows
    compute detrended ruggedness
    compute low-slope connectivity
    emit feature measurements + uncertainty + lineage
for each Earth unit:
    if eligibility fails:
        state = BLOCKED or NOT_COMPARABLE
    else:
        compute per-feature distances to Mars unit
        compute sensitivity scenarios
        compute Pareto status
        attach transfer-gap ledger
        attach field-feasibility metadata
emit stable/tie/indeterminate result
emit draft study protocol
validate every displayed value against evidence graph
```

## Scientific questions v0.1 can answer

- Are two curated terrain units distinguishable at the declared map scale?
- Which morphology descriptors drive the observed difference?
- Does the result flip when common support, masks, or thresholds change?
- Is the unit sufficiently documented for follow-up study design?
- What additional data would be required before a stronger claim?

## Questions v0.1 cannot answer

- Is a rover safe?
- Will autonomy generalize?
- Is traction equivalent?
- Is geology equivalent?
- Is the site physically permitted or operationally feasible?
- Does an Earth result predict a Mars result?

## Claim review protocol

Every sentence in the UI, README, demo, and docs is classified:

```text
FACT — source directly supports it
METHOD — generated by documented transformation
INFERENCE — reasonable but not directly measured
HYPOTHESIS — proposed for testing
UNKNOWN — data/evidence absent
PROHIBITED — must not be emitted
```

The release gate blocks any displayed “result” whose status is UNKNOWN, INFERENCE without label, or PROHIBITED.
