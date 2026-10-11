"""Data-sources citation / credits bundle for TerraTrace.

These are the UPSTREAM DATA PROVIDERS' required attributions: every DEM the
engine can ingest is published by a mission or agency (NASA PDS Geosciences,
USGS Astrogeology, ESA Copernicus, NASA/JAXA, ...) under its OWN terms, and must
be credited by any study, report, or product derived from it. This module reads
the machine-readable :mod:`terratrace.catalog` registry and produces, purely and
deterministically, a complete and correctly-attributed "Data sources & credits"
bundle, so that every TerraTrace artifact can carry proper citations and licence
notices (the project claims to be "citable" and provenance-complete).

The exact product actually retrieved at run time is pinned in ``sources.lock.yml``;
this module describes the CATALOG of sources and their attribution, not the single
file a given run downloaded.

Pure standard library: no third-party imports, no network, no disk access. The
companion script :mod:`scripts.make_references` is the only thing that writes a file.
"""
from __future__ import annotations

from . import catalog

# Deterministic body presentation order (reference planet first, then Earth, then
# the other reference bodies); any body not listed is appended, sorted by name.
_BODY_ORDER = ["mars", "earth", "moon", "mercury", "ceres"]
_BODY_TITLES = {"mars": "Mars", "earth": "Earth", "moon": "Moon",
                "mercury": "Mercury", "ceres": "Ceres"}
_KNOWN_BODIES = ("earth", "mars", "moon", "mercury", "ceres")

#: The exact, stable dict keys every reference record carries.
REFERENCE_FIELDS = ("id", "body", "provider", "product", "citation", "license",
                    "endpoint", "native_resolution_m")


def _body_title(body):
    """Display title for a body id ('mars' -> 'Mars'); robust to unknown bodies."""
    b = str(body or "").lower()
    return _BODY_TITLES.get(b, b.title() if b else "Unknown")


def _body_sort_key(body):
    """Sort key: known bodies in _BODY_ORDER, then any others alphabetically."""
    b = str(body or "").lower()
    return (_BODY_ORDER.index(b) if b in _BODY_ORDER else len(_BODY_ORDER), b)


def references_for(source_ids=None):
    """Return one attribution record per catalog source, deterministically ordered.

    source_ids: iterable of catalog ids, or None for ALL catalog sources.
    Each record is a plain dict with exactly ``REFERENCE_FIELDS``:
        id, body, provider, product, citation, license,
        endpoint (from the source's access block), native_resolution_m.
    Unknown ids raise KeyError (via ``catalog.get``) so a typo fails loudly.
    Ordered by (body presentation order, id) for reproducible output.
    """
    ids = catalog.all_ids() if source_ids is None else list(source_ids)
    records = []
    for sid in ids:
        s = catalog.get(sid)
        access = s.get("access", {}) or {}
        records.append({
            "id": s["id"],
            "body": s["body"],
            "provider": s["provider"],
            "product": s["product"],
            "citation": s["citation"],
            "license": s["license"],
            "endpoint": access.get("endpoint"),
            "native_resolution_m": s["native_resolution_m"],
        })
    records.sort(key=lambda r: (_body_sort_key(r["body"]), r["id"]))
    return records


def references_md(source_ids=None, title="Data sources & credits"):
    """Render a Markdown 'Data sources & credits' section, grouped BY BODY.

    source_ids: iterable of catalog ids, or None for ALL catalog sources.
    Sources appear under a per-body heading (Mars, Earth, Moon, ...), each as a
    bullet carrying product, provider, citation and licence. A short header line
    states that every dataset is used under its OWN provider terms (these are the
    upstream providers' required attributions, not TerraTrace's).
    Deterministic: identical input -> byte-identical output.
    """
    records = references_for(source_ids)
    out = []
    w = out.append
    w(f"## {title}")
    w("")
    w("TerraTrace derives its terrain products from the public planetary- and "
      "Earth-science archives below. Each dataset is used under ITS OWN provider "
      "terms and must be cited and credited accordingly; the attributions here are "
      "the upstream data providers' required credits. The exact product retrieved "
      "for any given study is pinned in `sources.lock.yml`.")
    w("")
    if not records:
        w("_No data sources selected._")
        return "\n".join(out).rstrip("\n") + "\n"
    # Group while preserving the (body-order, id) sort from references_for.
    by_body, body_seq = {}, []
    for r in records:
        if r["body"] not in by_body:
            by_body[r["body"]] = []
            body_seq.append(r["body"])
        by_body[r["body"]].append(r)
    for body in body_seq:
        w(f"### {_body_title(body)}")
        w("")
        for r in by_body[body]:
            res = r.get("native_resolution_m")
            res_txt = f"~{res:g} m" if isinstance(res, (int, float)) else "n/a"
            line = (f"- **{r['product']}** ({res_txt}) - {r['provider']}. "
                    f"{r['citation']} _Licence:_ {r['license']}.")
            endpoint = r.get("endpoint")
            if endpoint:
                line += f" Source: <{endpoint}>"
            w(line)
        w("")
    return "\n".join(out).rstrip("\n") + "\n"


def used_source_ids(package):
    """Best-effort, HEURISTIC guess at which catalog source ids a study package
    likely drew on, inferred from its profile's ``target_body`` and ``source_label``
    (and, as a secondary hint, the bodies named by its unit ids).

    This is deliberately conservative and NOT authoritative: a study package does
    not record the exact product it ingested (that is pinned in ``sources.lock.yml``).
    Rules:
      * no usable profile, or a SYNTHETIC study (``source_label`` mentions
        "synthetic") used no upstream dataset -> return ``[]``;
      * otherwise return the catalog sources for the target body, plus any other
        body whose name prefixes a unit id (a TerraTrace study compares a reference
        body against candidate units of another body).
    Returns a deterministically sorted list of catalog ids (possibly empty).
    """
    if not isinstance(package, dict):
        return []
    profile = package.get("profile")
    if not isinstance(profile, dict):
        return []
    source_label = str(profile.get("source_label", "")).lower()
    if "synthetic" in source_label:          # generated terrain, no catalog product
        return []
    bodies = set()
    tb = profile.get("target_body")
    if isinstance(tb, str) and tb.strip().lower() in _KNOWN_BODIES:
        bodies.add(tb.strip().lower())
    meta = package.get("unit_metadata")
    if isinstance(meta, dict):
        for uid in meta:
            if not isinstance(uid, str):
                continue
            low = uid.lower()
            for b in _KNOWN_BODIES:
                if low == b or low.startswith(b + "_"):
                    bodies.add(b)
    ids = []
    for b in bodies:
        ids.extend(s["id"] for s in catalog.by_body(b))
    return sorted(set(ids))


def credits_for_package(package):
    """Return a Markdown 'Data sources & credits' section tailored to a package.

    If :func:`used_source_ids` can name the sources, credit exactly those; otherwise
    (synthetic run, or no body hint) fall back to crediting the FULL catalog with a
    note that the specific product actually used is pinned in ``sources.lock.yml``.
    Always returns a non-empty Markdown string.
    """
    ids = used_source_ids(package)
    if ids:
        return references_md(ids)
    md = references_md()
    note = ("\n> Note: these are all data sources TerraTrace can ingest. This "
            "package did not record a specific upstream product (e.g. a synthetic "
            "run, or an unlabelled source); the exact product used in a real study "
            "is pinned in `sources.lock.yml`.\n")
    return md + note


# ---------------------------------------------------------------------------
# Method / algorithm references
#
# The records above credit the upstream DATA providers. The records below credit
# the published METHODS TerraTrace implements directly in NumPy (geomorphometry
# algorithms), which are a distinct category of citation. They are additive: the
# data-source bundle (references_for / references_md) is unchanged by this block.
# ---------------------------------------------------------------------------

#: The exact, stable dict keys every method-reference record carries. ``doi`` may
#: be ``None`` where the publication predates a registered DOI.
METHOD_REFERENCE_FIELDS = ("id", "topic", "citation", "doi")

#: Published algorithm references for the in-engine geomorphometric methods, in a
#: stable declaration order. Each is used only as a documented method; the authors
#: do not endorse TerraTrace.
METHOD_REFERENCES = (
    {
        "id": "openness_yokoyama_2002",
        "topic": "Topographic openness (positive & negative)",
        "citation": ("Yokoyama, R., Shirasawa, M., & Pike, R. J. (2002). "
                     "Visualizing topography by openness: a new application of "
                     "image processing to digital elevation models. "
                     "Photogrammetric Engineering & Remote Sensing, 68(3), 257-265."),
        "doi": None,
    },
    {
        "id": "geomorphons_jasiewicz_stepinski_2013",
        "topic": "Geomorphon landform classification",
        "citation": ("Jasiewicz, J., & Stepinski, T. F. (2013). Geomorphons - a "
                     "pattern recognition approach to classification and mapping "
                     "of landforms. Geomorphology, 182, 147-156."),
        "doi": "10.1016/j.geomorph.2012.11.005",
    },
)


def method_references():
    """Return the algorithm/method citations as a list of plain dicts.

    Each record carries exactly ``METHOD_REFERENCE_FIELDS`` (id, topic, citation,
    doi; ``doi`` may be ``None``). These credit the published METHODS TerraTrace
    implements in-engine - topographic openness (Yokoyama, Shirasawa & Pike 2002)
    and the geomorphon landform classifier (Jasiewicz & Stepinski 2013) - and are
    distinct from the upstream DATA-provider credits produced by
    :func:`references_for`. Returns fresh dict copies in declaration order.
    """
    return [dict(r) for r in METHOD_REFERENCES]


def method_references_md(title="Methods & algorithms cited"):
    """Render the algorithm/method citations as a Markdown section.

    Mirrors :func:`references_md`'s deterministic style but credits the published
    METHODS implemented in-engine rather than the data providers. Deterministic:
    identical call -> byte-identical output.
    """
    out = []
    w = out.append
    w(f"## {title}")
    w("")
    w("These credit the published algorithms TerraTrace implements directly in "
      "NumPy, distinct from the upstream data-provider credits above. Each is used "
      "only as a documented method; the authors do not endorse TerraTrace.")
    w("")
    for r in method_references():
        line = f"- {r['citation']}"
        doi = r.get("doi")
        if doi:
            line += f" doi:{doi}"
        w(line)
    return "\n".join(out).rstrip("\n") + "\n"
