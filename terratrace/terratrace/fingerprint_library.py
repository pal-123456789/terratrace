"""Cross-body terrain-fingerprint library and similarity search.

A thin, reusable *search* layer over :mod:`terratrace.fingerprint`: it turns a
collection of named reference terrains into a fingerprint library and answers
"which reference does this query terrain most resemble, morphologically?" --
including the cross-BODY case, where Earth candidate terrains are ranked
against each planetary reference's fingerprint (e.g. Mars- or Moon-like
references).

Every number this module reports is a *morphological* similarity ranking only.
A signature match here is NOT a classification, an identity match, a
geological-equivalence claim, or any traversability / mechanical / rover /
mission claim. "Most similar" means "nearest in the fixed morphology-signature
space of :data:`terratrace.fingerprint.FINGERPRINT_FIELDS`", and nothing more.
All feature math lives in :mod:`terratrace.fingerprint` /
:mod:`terratrace.descriptors`; this module only orchestrates it, so the claim
firewall of those layers is inherited unchanged.
"""
from __future__ import annotations

from . import fingerprint


def _as_fingerprint(terrain, dx=1.0, window=5):
    """Return a fingerprint dict for a raw array, or pass a dict through.

    Mirrors the "fingerprint dict OR raw elevation array" contract used across
    :mod:`terratrace.fingerprint`, so callers may freely mix pre-computed
    fingerprints and raw elevation tiles.
    """
    if isinstance(terrain, dict):
        return terrain
    return fingerprint.terrain_fingerprint(terrain, dx=dx, window=window)


def build_library(named_terrains, dx=1.0, window=5):
    """Fingerprint every named terrain into a ``{name: fingerprint-dict}`` library.

    ``named_terrains`` is a ``{name: 2D elevation array}`` mapping (already-built
    fingerprint dicts are passed through unchanged). Each array is reduced with
    :func:`terratrace.fingerprint.terrain_fingerprint` under the shared ``dx`` /
    ``window``; keys are preserved, so the result is a drop-in ``library`` for
    :func:`search` / :func:`cross_body_table`. Map-scale morphology only.
    """
    return {name: _as_fingerprint(terrain, dx=dx, window=window)
            for name, terrain in named_terrains.items()}


def search(query, library, dx=1.0, window=5, top=None, scales=None):
    """Rank a library of reference terrains by resemblance to ``query``.

    ``query`` is a fingerprint dict or a raw elevation array (fingerprinted once
    with ``dx`` / ``window``); ``library`` is a ``{name: fingerprint-or-array}``
    mapping (typically the output of :func:`build_library`). Delegates the
    ranking to :func:`terratrace.fingerprint.rank_library` (best morphological
    match first; ties broken by name ascending; non-comparable ``nan`` last) and
    truncates to the ``top`` best entries when ``top`` is given. ``scales`` is
    forwarded verbatim for per-dimension spread-normalisation. Returns a list of
    ``(name, similarity)``. Morphological resemblance only -- not a
    classification or identity claim.
    """
    query_fp = _as_fingerprint(query, dx=dx, window=window)
    ranked = fingerprint.rank_library(query_fp, library, scales=scales)
    return ranked if top is None else ranked[:top]


def cross_body_table(references, candidates, dx=1.0, window=5, scales=None):
    """Rank each candidate terrain against a set of cross-body references.

    Both ``references`` and ``candidates`` are ``{name: 2D array}`` mappings
    (raw tiles or pre-built fingerprint dicts). The archetypal cross-BODY use is
    planetary ``references`` (e.g. Mars- / Moon-like) with Earth ``candidates``.
    Both sides are fingerprinted with the shared ``dx`` / ``window`` and every
    candidate is ranked against every reference via
    :func:`terratrace.fingerprint.rank_library`. Returns a deterministic dict::

        {
          "references":     [reference names, sorted],
          "candidates":     [candidate names, sorted],
          "similarity":     {candidate: {reference: similarity_float}},
          "best_reference": {candidate: (reference_name, similarity)},
        }

    where ``best_reference`` names, per candidate, the single reference it most
    resembles morphologically (``rank_library``'s top entry, so ties break by
    reference name ascending). Each inner ``similarity`` dict is ordered by
    sorted reference name for stable output. ``scales`` is forwarded for
    spread-normalised comparison. Morphological resemblance only -- never a
    geological-equivalence or mission claim.
    """
    ref_lib = build_library(references, dx=dx, window=window)
    cand_lib = build_library(candidates, dx=dx, window=window)
    ref_names = sorted(ref_lib)
    cand_names = sorted(cand_lib)

    similarity_map = {}
    best_reference = {}
    for cand in cand_names:
        ranked = fingerprint.rank_library(cand_lib[cand], ref_lib, scales=scales)
        by_ref = dict(ranked)
        similarity_map[cand] = {ref: by_ref[ref] for ref in ref_names}
        best_reference[cand] = ranked[0] if ranked else (None, float("nan"))

    return {
        "references": ref_names,
        "candidates": cand_names,
        "similarity": similarity_map,
        "best_reference": best_reference,
    }


def library_scales_from(terrains_or_fps, dx=1.0, window=5):
    """Per-dimension spread of a terrain/fingerprint library (passthrough).

    Thin forwarder to :func:`terratrace.fingerprint.library_scales`: given a
    ``{name: fingerprint-or-array}`` mapping it returns the per-
    :data:`terratrace.fingerprint.FINGERPRINT_FIELDS` standard deviation across
    the library, suitable to pass as ``scales`` to :func:`search` /
    :func:`cross_body_table` so no single large-magnitude descriptor dominates
    the distance. Degenerate spreads are floored by the underlying helper.
    """
    return fingerprint.library_scales(terrains_or_fps, dx=dx, window=window)
