"""Reproducibility and integrity tooling for TerraTrace study packages.

A reviewer can confirm that a published study package is authentic and
reproducible without re-trusting the pipeline that produced it:

* ``recompute_hash`` / ``verify_hash`` recompute the content hash of a package
  exactly as :mod:`terratrace.study` does (SHA-256 over the canonical JSON of
  every top-level key except ``package_hash``) and compare it against the stored
  value, so a tampered or truncated package is detected.
* ``diff_packages`` reports which top-level keys differ between two packages.
* ``verify_synthetic_reproducible`` re-runs the deterministic synthetic study
  twice and confirms the two runs agree bit-for-bit.

This module adds integrity verification only. It introduces no new scientific
claim, metric, or decision; it merely re-checks the hashes the study already
emits.
"""
from __future__ import annotations

import json

from terratrace import provenance, study


def _canonical_json(obj) -> str:
    """Canonical JSON used for value comparison (matches the hashing form)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"))


def recompute_hash(package) -> str:
    """Recompute the package content hash exactly as the study pipeline does.

    The hash covers the canonical JSON of every top-level key except
    ``package_hash`` itself, mirroring ``study.compare_units``.
    """
    return provenance.sha256_json(
        {k: v for k, v in package.items() if k != "package_hash"})


def verify_hash(package) -> dict:
    """Compare the stored ``package_hash`` against a freshly recomputed one.

    Returns ``{"stored", "recomputed", "match"}``. A package whose stored hash
    was tampered with reports ``match`` False; a package missing the key reports
    ``stored`` None and ``match`` False (no exception).
    """
    stored = package.get("package_hash")
    recomputed = recompute_hash(package)
    return {"stored": stored, "recomputed": recomputed,
            "match": stored is not None and stored == recomputed}


def diff_packages(p1, p2, keys=None) -> list[str]:
    """Return the sorted top-level keys whose values differ between two packages.

    Values are compared by canonical JSON, so ordering/formatting differences do
    not register as changes. With ``keys`` given, only those keys are examined;
    otherwise the union of both packages' keys is used, and a key present in only
    one package counts as a difference. Ordering is deterministic (sorted).
    """
    missing = object()
    candidates = set(keys) if keys is not None else set(p1) | set(p2)
    out = []
    for k in candidates:
        a = p1.get(k, missing)
        b = p2.get(k, missing)
        if (a is missing) != (b is missing):
            out.append(k)
        elif a is not missing and _canonical_json(a) != _canonical_json(b):
            out.append(k)
    return sorted(out)


def verify_synthetic_reproducible(**run_study_kwargs) -> dict:
    """Run the synthetic study twice and confirm the content hashes agree.

    With no kwargs the defaults reproduce the canonical synthetic study. Returns
    ``{"hash": <first run package_hash>, "match": <both runs equal>}``.
    """
    h1 = study.run_study(**run_study_kwargs)["package_hash"]
    h2 = study.run_study(**run_study_kwargs)["package_hash"]
    return {"hash": h1, "match": h1 == h2}
