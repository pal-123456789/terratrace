"""Terrain morphological fingerprint and similarity ranking.

A *fingerprint* is a compact, fixed-length signature vector of map-scale
morphology descriptors distilled from
:func:`terratrace.descriptors.descriptor_bank`. Two fingerprints can be
compared with :func:`similarity`, and a query terrain can be ranked against
a library of references with :func:`rank_library`, answering the question:
"which reference terrain does this most resemble, morphologically?"

Claim firewall (inherited from the feature / descriptor layers): every
number in a fingerprint is a map-scale morphology descriptor, and the
similarity it induces is a *morphological* resemblance only. This is NOT a
classification, an identity match, a geological-equivalence claim, or any
traversability / mechanical / rover / mission claim. "Most similar" means
"nearest in this morphology-signature space", and nothing more.
"""
from __future__ import annotations

import numpy as np

from . import descriptors

# Fixed, documented signature: a stable subset of descriptor_bank scalars
# chosen to span complementary morphology axes -- overall steepness
# (slope p50 / p90), local vertical scale (relief p50), detrended and
# vector ruggedness, surface rugosity, curvature spread, aspect isotropy,
# the hypsometric integral, landform organisation (TPI dispersion) and the
# roughness-vs-scale (Hurst) exponent. A dotted name indexes a summarised
# map feature's statistic ("slope.p50"); a bare name is a scalar descriptor.
# Every name is verified present in descriptor_bank's output.
FINGERPRINT_FIELDS = (
    "slope.p50",
    "slope.p90",
    "relief.p50",
    "ruggedness.p50",
    "surface_area_ratio.p50",
    "mean_curvature.std",
    "vector_ruggedness.p50",
    "aspect_dispersion",
    "hypsometric_integral",
    "tpi_dispersion",
    "hurst_exponent",
)


def _pull(bank, field):
    """Resolve one FINGERPRINT_FIELDS name against a descriptor bank.

    A dotted name ("slope.p50") indexes a summarised map feature's statistic;
    a bare name ("aspect_dispersion") is a scalar descriptor. Always returns a
    plain ``float``.
    """
    if "." in field:
        key, stat = field.split(".", 1)
        return float(bank[key][stat])
    return float(bank[field])


def terrain_fingerprint(z, dx=1.0, window=5):
    """Compute the morphological fingerprint of one elevation tile.

    Runs :func:`descriptors.descriptor_bank` once and pulls the fixed subset
    named by :data:`FINGERPRINT_FIELDS` into an insertion-ordered
    ``{field_name: float}`` dict (same order as FINGERPRINT_FIELDS). Every
    value is a plain ``float`` -- ``nan`` where a descriptor is undefined
    (e.g. the Hurst exponent or hypsometric integral of a perfectly flat
    tile) -- so the result is JSON-serialisable and deterministic for a given
    array. Map-scale morphology only; see the module docstring.
    """
    bank = descriptors.descriptor_bank(z, dx=dx, window=window)
    return {field: _pull(bank, field) for field in FINGERPRINT_FIELDS}


def fingerprint_vector(fp_or_z, dx=1.0, window=5):
    """Return a fingerprint as an ordered tuple in FINGERPRINT_FIELDS order.

    ``fp_or_z`` is either a fingerprint dict (read directly) or a raw
    elevation array (a fingerprint is computed from it with ``dx`` /
    ``window``). The tuple is positionally aligned with
    :data:`FINGERPRINT_FIELDS`; every element is a plain float.
    """
    fp = (fp_or_z if isinstance(fp_or_z, dict)
          else terrain_fingerprint(fp_or_z, dx=dx, window=window))
    return tuple(float(fp[field]) for field in FINGERPRINT_FIELDS)


def similarity(fp_a, fp_b, scales=None):
    """Morphological similarity in (0, 1]; 1.0 iff the signatures are identical.

    Builds both fingerprint vectors (via :func:`fingerprint_vector`, so dicts
    or raw arrays are accepted), divides each dimension ``i`` by ``scales[i]``
    (per-dimension normalisation; ``1.0`` for every dimension when ``scales``
    is ``None``), and forms the per-dimension-normalised root-mean-square
    (RMS) Euclidean distance

        d = sqrt( mean_i ( (a_i - b_i) / s_i )^2 )

    over the *pairwise-complete* dimensions only: any dimension where either
    value -- or its scale -- is non-finite, or whose scale is zero, is
    skipped, and the mean is taken over the dimensions that remain (so the
    distance stays on the same footing regardless of how many were dropped).
    The distance is mapped to a bounded similarity by

        sim = 1 / (1 + d)

    so identical signatures give ``d = 0`` -> ``sim = 1.0`` and similarity
    decays monotonically toward 0 as the signatures diverge. Returns ``nan``
    when no dimension is pairwise-complete.
    """
    va = np.asarray(fingerprint_vector(fp_a), dtype=float)
    vb = np.asarray(fingerprint_vector(fp_b), dtype=float)
    n = len(FINGERPRINT_FIELDS)
    s = np.ones(n) if scales is None else np.asarray(scales, dtype=float).ravel()
    if s.size != n:
        raise ValueError("scales must have length len(FINGERPRINT_FIELDS)")
    valid = np.isfinite(va) & np.isfinite(vb) & np.isfinite(s) & (s != 0.0)
    if not valid.any():
        return float("nan")
    diff = (va[valid] - vb[valid]) / s[valid]
    d = float(np.sqrt(np.mean(diff ** 2)))
    return 1.0 / (1.0 + d)


def rank_library(query, library, scales=None):
    """Rank reference terrains by morphological similarity to ``query``.

    ``query`` is a fingerprint dict or a raw elevation array; ``library`` is a
    ``{name: fingerprint-or-array}`` mapping. Returns a list of
    ``(name, similarity)`` sorted by similarity DESCENDING -- the best
    morphological match first -- with ties broken by ``name`` ascending and
    ``nan`` similarities (no comparable dimension) sorted last. ``scales`` is
    forwarded to :func:`similarity`; the query fingerprint is computed once.
    Morphological resemblance only; not a classification or identity claim.
    """
    q = query if isinstance(query, dict) else terrain_fingerprint(query)
    ranked = [(name, similarity(q, ref, scales=scales))
              for name, ref in library.items()]

    def _key(item):
        name, sim = item
        ordered = sim if np.isfinite(sim) else float("-inf")
        return (-ordered, name)

    ranked.sort(key=_key)
    return ranked


def library_scales(library, dx=1.0, window=5, floor=1e-9):
    """Per-dimension spread of a fingerprint library, for use as ``scales``.

    Returns, per :data:`FINGERPRINT_FIELDS` dimension, the standard deviation
    across the library's fingerprints (finite values only). Passing it as
    ``scales`` to :func:`similarity` / :func:`rank_library` puts every
    dimension on a comparable, unit-free footing instead of letting the
    largest-magnitude descriptor dominate the raw distance. Degenerate
    (zero / undefined) spreads are floored to ``floor`` so they never divide
    by zero. Library values may be fingerprint dicts or raw arrays.
    """
    vecs = [fingerprint_vector(v, dx=dx, window=window) for v in library.values()]
    if not vecs:
        return tuple(1.0 for _ in FINGERPRINT_FIELDS)
    mat = np.asarray(vecs, dtype=float)
    out = []
    for j in range(mat.shape[1]):
        col = mat[:, j][np.isfinite(mat[:, j])]
        spread = float(np.std(col)) if col.size else 0.0
        out.append(spread if spread > floor else float(floor))
    return tuple(out)
