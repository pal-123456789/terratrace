"""One-command study DELIVERABLE bundle for TerraTrace.

:func:`export_bundle` writes a complete, self-consistent study deliverable to a
single directory in one call: the JSON study package, a Markdown report, a
self-contained offline HTML report, a data-sources credits file, the offline
HTML viewer, and a ``CHECKSUMS.txt`` manifest -- everything a user needs to
share or review a study at once.

This module only PACKAGES what the engine already emitted. It renders through
the existing report / report_html / references / build_viewer renderers, each of
which reproduces the package's map-scale-morphology CLAIM FIREWALL verbatim (the
prohibited-claims list, the transfer-gap ledger, and the draft protocol). The
bundle never widens, softens, re-weights, or invents a claim; it inherits the
engine's scientific boundary (morphology screening only -- no traversability,
autonomy, geologic-equivalence, site-access, or mission-readiness claim).

Output is deterministic: for a fixed package the rendered artifacts are
byte-identical, so the checksums are reproducible. Pure standard library at
import time; the heavy renderers are imported lazily inside :func:`export_bundle`
so merely importing this module stays light.
"""
from __future__ import annotations

import hashlib
import json
import os

#: Rendered artifacts, in the fixed order they are written and checksummed.
STUDY_JSON = "study.json"
REPORT_MD = "report.md"
REPORT_HTML = "report.html"
REFERENCES_MD = "REFERENCES.md"
VIEWER_HTML = "viewer.html"
CHECKSUMS = "CHECKSUMS.txt"


def _sha256_hex(data):
    """Hex SHA-256 digest of a ``bytes`` object (stdlib hashlib)."""
    return hashlib.sha256(data).hexdigest()


def export_bundle(package, outdir):
    """Write a complete study deliverable to ``outdir`` and return a manifest.

    Creates ``outdir`` and writes six files: ``study.json`` (the package, pretty
    and key-sorted), ``report.md`` (Markdown report), ``report.html`` (self-
    contained HTML report), ``REFERENCES.md`` (data-sources credits),
    ``viewer.html`` (offline viewer), and ``CHECKSUMS.txt`` (one
    ``"<sha256>  <filename>"`` line per rendered artifact, computed on the exact
    bytes written). Every file is written as UTF-8 with ``\\n`` line endings in
    binary mode, so each recorded checksum matches the on-disk bytes exactly on
    any platform.

    Returns a manifest dict::

        {"outdir": <path>,
         "files": {name: {"bytes": int, "sha256": hex}, ...},
         "package_hash": <package's own hash or None>}

    The heavy renderers are imported lazily here so importing this module is
    cheap. Nothing in this function widens the package's claim firewall.
    """
    from . import report, report_html, references, build_viewer

    os.makedirs(outdir, exist_ok=True)

    rendered = [
        (STUDY_JSON, json.dumps(package, indent=2, sort_keys=True)),
        (REPORT_MD, report.study_report_md(package)),
        (REPORT_HTML, report_html.study_report_html(package)),
        (REFERENCES_MD, references.credits_for_package(package)),
        (VIEWER_HTML, build_viewer.build_html(package)),
    ]

    files, checksum_lines = {}, []
    for name, text in rendered:
        data = text.encode("utf-8")
        with open(os.path.join(outdir, name), "wb") as fh:
            fh.write(data)
        digest = _sha256_hex(data)
        files[name] = {"bytes": len(data), "sha256": digest}
        checksum_lines.append(f"{digest}  {name}")

    checksums = ("\n".join(checksum_lines) + "\n").encode("utf-8")
    with open(os.path.join(outdir, CHECKSUMS), "wb") as fh:
        fh.write(checksums)
    files[CHECKSUMS] = {"bytes": len(checksums), "sha256": _sha256_hex(checksums)}

    return {"outdir": os.fspath(outdir), "files": files,
            "package_hash": package.get("package_hash") if isinstance(package, dict) else None}


def write_manifest(manifest, outdir):
    """Also dump ``manifest`` as ``bundle_manifest.json`` in ``outdir``.

    Written as pretty, key-sorted UTF-8 (binary mode). Returns the file path.
    """
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, "bundle_manifest.json")
    with open(path, "wb") as fh:
        fh.write(json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8"))
    return path
