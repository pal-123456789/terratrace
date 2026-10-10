"""Transparent, rule-based terrain-TYPE classifier (map-scale morphology).

This module assigns a tile a single QUALITATIVE morphological *type* from the
descriptor bank of :mod:`terratrace.descriptors`, using EXPLICIT, documented
threshold rules -- there is no machine learning, no training, no fitted model
and no randomness anywhere in this file. Every decision is a comparison of a
robust descriptor against a named constant defined below, so the label is fully
auditable and reproducible.

Claim firewall (inherited from the feature/descriptor layers): the type is a
DESCRIPTIVE map-scale morphology label -- a shorthand for *how rough, how
dissected, how much relief* the summarised surface shows. It is **not** a
geological, genetic, lithological, stratigraphic, age, hazard, mission or
rover-traversability classification. "flat_plain" does not assert the ground is
safe to drive on; "rough_rugged" does not assert bedrock, boulders, or any
mechanical property. Summarising morphology into a word adds no claim that the
underlying descriptors do not already carry.

Vocabulary (4 types), from least to most relief/dissection:

* ``flat_plain``       -- very low slope + very low local relief + locally
                          planar (near-zero detrended ruggedness).
* ``rolling``          -- clear slope and relief but a SMOOTH, long-correlated
                          surface (low detrended ruggedness, high Hurst, low
                          vector ruggedness); hill-like.
* ``dissected_upland`` -- moderate slope with an organised ridge-AND-valley
                          landform mix and moderate (not extreme) ruggedness.
* ``rough_rugged``     -- high detrended ruggedness / high TRI / high vector
                          ruggedness / low Hurst / wide slope spread.

Scoring is a transparent membership vote: each type owns a short list of
documented boolean criteria, and its score is simply the FRACTION of its
criteria that the tile satisfies (so every score is in [0, 1]). The chosen
type is the argmax; ties break by the fixed :data:`TYPES` order. Confidence is
the margin between the top score and the runner-up (also in [0, 1]).
"""
from __future__ import annotations

# --- Type vocabulary, ordered least -> most relief/dissection. The order also
#     serves as the deterministic tie-break when two types score equally. ------
TYPES = ("flat_plain", "rolling", "dissected_upland", "rough_rugged")

# --- Documented thresholds (all comparisons below use ONLY these constants) ---
# "Flat" = tiny absolute height variation in every robust channel.
FLAT_SLOPE_MAX_DEG = 2.0      # median slope below this is effectively level
FLAT_RELIEF_MAX = 0.25        # median local relief (elevation units)
FLAT_TRI_MAX = 0.10           # mean Terrain Ruggedness Index (RMS neighbour diff)

# "Smooth" = locally planar surface (a plane OR a smooth dome both qualify).
SMOOTH_RUGG_MAX = 0.5         # detrended ruggedness p50 below this = smooth
SMOOTH_VRM_MAX = 0.1          # vector ruggedness p50 below this = smooth
SMOOTH_HURST_MIN = 0.6        # Hurst above this = long-correlated / smooth

# "Non-flat" gates for a surface that has genuine slope and relief.
NONFLAT_SLOPE_MIN_DEG = 2.0
NONFLAT_RELIEF_MIN = 0.25

# "Dissected" = organised ridge+valley structure, moderate (bounded) ruggedness.
DISSECT_SLOPE_MIN_DEG = 3.0
DISSECT_LANDFORM_MIN = 0.10   # BOTH ridge and valley fractions must exceed this
DISSECT_RUGG_MIN = 0.5        # more broken than a smooth hill ...
DISSECT_RUGG_MAX = 3.0        # ... but not as extreme as rough_rugged
DISSECT_HURST_MIN = 0.2       # intermediate roughness scaling
DISSECT_HURST_MAX = 0.7

# "Rough" = strong local non-planarity / near-white-noise roughness scaling.
ROUGH_RUGG_MIN = 0.5          # detrended ruggedness p50 above this = rough
ROUGH_TRI_MIN = 1.0           # mean TRI above this = rough
ROUGH_VRM_MIN = 0.1           # vector ruggedness p50 above this = rugged
ROUGH_HURST_MAX = 0.4         # Hurst below this = rough / short-correlated
ROUGH_SLOPE_STD_MIN = 10.0    # wide slope spread (degrees)

_NAN = float("nan")


def _summ(bank, key, stat):
    """Return ``bank[key][stat]`` as a float, or NaN if absent/degenerate."""
    d = bank.get(key)
    if isinstance(d, dict):
        try:
            return float(d.get(stat, _NAN))
        except (TypeError, ValueError):
            return _NAN
    return _NAN


def _extract_evidence(bank):
    """Pull the robust descriptors the rules read into a flat float dict.

    These are exactly the values compared against the documented thresholds, so
    the returned dict IS the evidence that drives the decision. Missing or
    degenerate entries become NaN; NaN simply fails every threshold comparison
    (Python NaN comparisons are False), so a degenerate bank never raises.
    """
    lf = bank.get("landform_fraction")
    if not isinstance(lf, dict):
        lf = {}

    def lff(name):
        try:
            return float(lf.get(name, _NAN))
        except (TypeError, ValueError):
            return _NAN

    hurst = bank.get("hurst_exponent", _NAN)
    try:
        hurst = float(hurst)
    except (TypeError, ValueError):
        hurst = _NAN

    return {
        "slope_p50": _summ(bank, "slope", "p50"),
        "slope_std": _summ(bank, "slope", "std"),
        "relief_p50": _summ(bank, "relief", "p50"),
        "ruggedness_p50": _summ(bank, "ruggedness", "p50"),
        "terrain_ruggedness_index_mean": _summ(bank, "terrain_ruggedness_index", "mean"),
        "vector_ruggedness_p50": _summ(bank, "vector_ruggedness", "p50"),
        "hurst_exponent": hurst,
        "landform_ridge": lff("ridge"),
        "landform_valley": lff("valley"),
        "landform_flat": lff("flat"),
    }


def _type_criteria(e):
    """Return ``{type: [bool, ...]}`` -- the documented criteria per type.

    Each list is this type's membership vote; the type score is the mean of its
    booleans (fraction satisfied), always in [0, 1]. The rules are evaluated in
    the fixed order below and are side-effect free.
    """
    slope_p50 = e["slope_p50"]
    slope_std = e["slope_std"]
    relief_p50 = e["relief_p50"]
    rugg_p50 = e["ruggedness_p50"]
    tri_mean = e["terrain_ruggedness_index_mean"]
    vrm_p50 = e["vector_ruggedness_p50"]
    hurst = e["hurst_exponent"]
    ridge = e["landform_ridge"]
    valley = e["landform_valley"]

    return {
        # Very low slope, relief and TRI, and locally planar.
        "flat_plain": [
            slope_p50 < FLAT_SLOPE_MAX_DEG,
            relief_p50 < FLAT_RELIEF_MAX,
            tri_mean < FLAT_TRI_MAX,
            rugg_p50 < SMOOTH_RUGG_MAX,
        ],
        # Real slope + relief, but a smooth / long-correlated surface.
        "rolling": [
            slope_p50 >= NONFLAT_SLOPE_MIN_DEG,
            relief_p50 >= NONFLAT_RELIEF_MIN,
            rugg_p50 < SMOOTH_RUGG_MAX,
            hurst > SMOOTH_HURST_MIN,
            vrm_p50 < SMOOTH_VRM_MAX,
        ],
        # Moderate slope with organised ridge AND valley, bounded ruggedness.
        "dissected_upland": [
            slope_p50 >= DISSECT_SLOPE_MIN_DEG,
            (ridge > DISSECT_LANDFORM_MIN) and (valley > DISSECT_LANDFORM_MIN),
            DISSECT_RUGG_MIN <= rugg_p50 <= DISSECT_RUGG_MAX,
            DISSECT_HURST_MIN <= hurst <= DISSECT_HURST_MAX,
        ],
        # Strong local non-planarity / near-white-noise roughness scaling.
        "rough_rugged": [
            rugg_p50 > ROUGH_RUGG_MIN,
            tri_mean > ROUGH_TRI_MIN,
            vrm_p50 > ROUGH_VRM_MIN,
            hurst < ROUGH_HURST_MAX,
            slope_std > ROUGH_SLOPE_STD_MIN,
        ],
    }


def classify_bank(bank, dx=None):
    """Classify an ALREADY-computed :func:`descriptors.descriptor_bank` dict.

    ``dx`` is accepted for API symmetry with :func:`classify` but is not used:
    the bank already encodes every pixel-size-dependent feature (slope is in
    degrees, relief/ruggedness in elevation units), so the label depends only on
    the bank. Deterministic and side-effect free.

    Returns a dict with:

    * ``type``       -- the chosen type (one of :data:`TYPES`);
    * ``confidence`` -- top score minus runner-up score, clamped to [0, 1];
    * ``evidence``   -- the robust descriptor values the rules read;
    * ``scores``     -- ``{type: fraction_of_criteria_met}`` for every type.
    """
    del dx  # intentionally unused; see docstring.
    evidence = _extract_evidence(bank)
    criteria = _type_criteria(evidence)

    scores = {}
    for name in TYPES:  # fixed order -> deterministic dict
        votes = criteria[name]
        scores[name] = (sum(1 for v in votes if v) / len(votes)) if votes else 0.0

    # Argmax with a deterministic tie-break by the documented TYPES order.
    ordered = sorted(scores.items(), key=lambda kv: (-kv[1], TYPES.index(kv[0])))
    top_type, top_score = ordered[0]
    second_score = ordered[1][1] if len(ordered) > 1 else 0.0
    confidence = max(0.0, min(1.0, top_score - second_score))

    return {
        "type": top_type,
        "confidence": float(confidence),
        "evidence": evidence,
        "scores": scores,
    }


def classify(z, dx=1.0, window=5):
    """Compute the descriptor bank for ``z`` then :func:`classify_bank` it.

    ``dx`` is the (square) pixel size in metres and ``window`` the odd window
    passed through to :func:`descriptors.descriptor_bank`. Deterministic: the
    same array always yields an equal dict. The result carries the same claim
    firewall as the module docstring -- a descriptive map-scale morphology label
    only.
    """
    from . import descriptors
    bank = descriptors.descriptor_bank(z, dx=dx, window=window)
    return classify_bank(bank, dx=dx)
