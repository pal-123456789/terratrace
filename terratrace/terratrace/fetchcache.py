"""Idempotent fetch cache + provenance manifest for real-DEM downloads.

Downloading planetary DEMs is expensive (often gigabytes per tile), so re-running
a fetch should *skip* files that are already present on disk -- and, when a
checksum is known, already verified -- instead of pulling the bytes again. This
module provides the pure-stdlib bookkeeping for that:

  * ``needs_fetch`` answers "do I actually have to download this?" from the file's
    presence, size, and (optionally) its expected SHA-256, so a caller can short
    out a no-op download.
  * ``record_entry`` + the ``*_manifest`` helpers maintain a small JSON manifest
    keyed by config-unit id, recording what was fetched, where it landed, its size
    and digest, and when it was recorded.

The manifest is a lightweight, mutable *operational* record of fetch runs. It
complements -- and does NOT replace -- ``sources.lock.yml`` (the authoritative,
citation-bearing provenance lock built by ``sourcelock``): the lock is the
reproducibility/attribution record, while this manifest is the download cache
ledger. The SHA-256 computed here is byte-for-byte identical to the lock's digest
(see ``sha256_file`` below), so the two always agree on file identity.

Pure stdlib only (hashlib, json, os, datetime). No network, no rasterio, no numpy,
no third-party dependencies.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


def _utc_now_iso():
    """Timezone-aware UTC timestamp as ISO-8601, e.g. '2026-10-10T12:00:00Z'."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256_file(path, chunk=1 << 20):
    """Streamed SHA-256 hex digest of a file.

    Identical implementation (and therefore identical digest) to
    ``sourcelock.sha256_file`` -- same 1 MiB chunking, same hashlib call -- so the
    fetch manifest and the source-lock never disagree on a file's hash.
    """
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def file_ok(path, min_bytes=1):
    """True when ``path`` exists, is a regular file, and is at least ``min_bytes``."""
    return os.path.isfile(path) and os.path.getsize(path) >= min_bytes


def needs_fetch(path, expected_sha256=None, min_bytes=1):
    """Decide whether ``path`` still needs downloading.

    Returns ``(need, reason)``:
      * ``(True, "missing or empty")`` when the file is absent or below min_bytes.
      * ``(True, "checksum mismatch")`` when ``expected_sha256`` is given and does
        not match the file's digest (compared case-insensitively).
      * ``(False, "cached")`` otherwise.
    """
    if not file_ok(path, min_bytes=min_bytes):
        return True, "missing or empty"
    if expected_sha256 is not None and sha256_file(path).lower() != expected_sha256.lower():
        return True, "checksum mismatch"
    return False, "cached"


def record_entry(unit, path=None, source_id=None):
    """Build one manifest entry for a config-unit dict.

    ``unit`` has at least ``id`` and usually ``bbox``, ``path`` and ``body``.
    ``path`` defaults to ``unit.get("path")``. SHA-256 and byte count are computed
    only when the file is actually present; otherwise they are ``None`` and
    ``exists`` is ``False``.
    """
    if path is None:
        path = unit.get("path")
    exists = path is not None and os.path.isfile(path)
    return {
        "id": unit.get("id"),
        "path": path,
        "source_id": source_id,
        "body": unit.get("body"),
        "bbox": unit.get("bbox"),
        "exists": bool(exists),
        "sha256": sha256_file(path) if exists else None,
        "bytes": os.path.getsize(path) if exists else None,
        "fetched_at": _utc_now_iso(),
    }


def load_manifest(manifest_path):
    """Load a fetch manifest, returning the empty shape if the file is missing.

    Robust to an absent manifest (first run): returns
    ``{"entries": {}, "updated_at": None}`` rather than raising.
    """
    if not os.path.isfile(manifest_path):
        return {"entries": {}, "updated_at": None}
    with open(manifest_path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def update_manifest(manifest, entry):
    """Insert or replace ``entry`` under ``manifest["entries"][entry["id"]]``.

    Other entries are preserved; ``updated_at`` is refreshed to now (UTC ISO). The
    ``entries`` key is created if absent. Returns the (mutated) manifest.
    """
    if not isinstance(manifest.get("entries"), dict):
        manifest["entries"] = {}
    manifest["entries"][entry["id"]] = entry
    manifest["updated_at"] = _utc_now_iso()
    return manifest


def save_manifest(manifest_path, manifest):
    """Write ``manifest`` as pretty, deterministic JSON; return ``manifest_path``.

    Parent directories are created as needed. JSON is written with ``indent=2`` and
    ``sort_keys=True`` (utf-8) so manifests diff cleanly across runs.
    """
    parent = os.path.dirname(manifest_path)
    if parent:
        os.makedirs(parent, exist_ok=True)
    with open(manifest_path, "w", encoding="utf-8") as fh:
        json.dump(manifest, fh, indent=2, sort_keys=True)
    return manifest_path
