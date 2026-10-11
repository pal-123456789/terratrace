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

from . import descriptors, geomorphons, spectral, anisotropy

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

# Key under which the OPTIONAL landform component (a normalised 9x9 geomorphon
# spectrum, as a nested list of floats) is stored inside a fingerprint when it
# is built with ``include_landform=True``. It is additive: the FINGERPRINT_FIELDS
# scalars above are untouched, so a default fingerprint is byte-identical to one
# built before this component existed.
LANDFORM_SPECTRUM_KEY = "landform_spectrum"

# Key under which the OPTIONAL scale/fabric component is stored inside a
# fingerprint when it is built with ``include_scale_fabric=True``. The value is
# a flat ``{field: float}`` dict over :data:`SCALE_FABRIC_FIELDS`: the log-log
# spectral slope, the three roughness-band RATIOS (per-band RMS normalised by
# their sum, so they form a scale-free wavelength shape summing to ~1) and the
# directional-fabric anisotropy strength. Like the landform component it is
# purely additive: the FINGERPRINT_FIELDS scalars are untouched, so a default
# fingerprint stays byte-identical to one built before this component existed.
# Every field is dx-INVARIANT (the spectral slope and the band partition are
# unchanged by a constant rescaling of wavenumber, and the fabric strength does
# not use dx), so the on-the-fly path may safely scan at ``dx=1.0``.
SCALE_FABRIC_KEY = "scale_fabric"
SCALE_FABRIC_FIELDS = (
    "spectral_slope",
    "rough_long_ratio",
    "rough_mid_ratio",
    "rough_short_ratio",
    "anisotropy_strength",
)

# Documented reference span for the spectral-slope sub-distance: a difference of
# this many log-log-slope units is treated as a "full" (==1) separation on that
# axis. Chosen to bracket the plausible range of terrain spectral slopes.
SCALE_FABRIC_SLOPE_SPAN = 4.0

# Key under which the OPTIONAL texture-battery component is stored inside a
# fingerprint when it is built with ``include_texture=True``. The value is a flat
# ``{field: float}`` dict over :data:`TEXTURE_FIELDS`: the log-log spectral slope
# (:func:`terratrace.spectral.spectral_signature`), the differential box-counting
# fractal dimension (:func:`terratrace.fractal.box_counting_dimension`), the
# normalised slope entropy (:func:`terratrace.entropy_terrain.entropy_signature`)
# and the r=2 gliding-box lacunarity
# (:func:`terratrace.lacunarity.lacunarity_signature`) -- four complementary
# map-scale TEXTURE / surface-complexity descriptors. Like the landform and
# scale/fabric components it is purely additive: the FINGERPRINT_FIELDS scalars
# are untouched, so a default fingerprint stays byte-identical to one built before
# this component existed.
TEXTURE_KEY = "texture"
TEXTURE_FIELDS = (
    "spectral_slope",
    "fractal_dim",
    "slope_entropy_norm",
    "lacunarity_r2",
)

# Documented reference spans for the texture sub-distances, one per
# :data:`TEXTURE_FIELDS` entry: on each axis a difference of this many native
# units is treated as a "full" (==1) separation, so the per-scalar sub-distance
# is ``min(1, |a - b| / span)`` and the averaged texture term stays bounded in
# ``[0, 1]`` even though the raw scalars live on very different scales:
#   * ``spectral_slope``     -- log-log slope units (matches
#     :data:`SCALE_FABRIC_SLOPE_SPAN`; brackets the plausible terrain range);
#   * ``fractal_dim``        -- the box-counting dimension is confined to
#     ``[2, 3]``, so its full physical range is exactly 1.0;
#   * ``slope_entropy_norm`` -- already a normalised ``[0, 1]`` diversity index,
#     so its full range is 1.0;
#   * ``lacunarity_r2``      -- Lambda(2) is ``>= 1`` and unbounded above; a span
#     of 1.0 brackets the spread seen across terrain tiles while keeping the term
#     bounded (larger gaps simply saturate at 1).
TEXTURE_SPANS = {
    "spectral_slope": 4.0,
    "fractal_dim": 1.0,
    "slope_entropy_norm": 1.0,
    "lacunarity_r2": 1.0,
}

# Key under which the OPTIONAL geostatistical-structure component is stored inside
# a fingerprint when it is built with ``include_geostat=True``. The value is a flat
# ``{field: float}`` dict over :data:`GEOSTAT_FIELDS`: two scale-aware second-order
# structure scalars -- the variogram log-log roughness-scaling slope
# (:func:`terratrace.variogram.variogram_signature`) and the surface-normal fabric
# isotropy (:func:`terratrace.fabric_eigen.fabric_signature`) -- followed by the six
# Wood (1996) curvature-feature area fractions
# (:func:`terratrace.curvature_classes.curvature_class_signature`), stored as
# ``curv_<class>`` in :data:`terratrace.curvature_classes.CLASS_NAMES` order and
# forming a composition that sums to ~1. Like the landform, scale/fabric and texture
# components it is purely additive: the FINGERPRINT_FIELDS scalars are untouched, so a
# default fingerprint stays byte-identical to one built before this component existed.
GEOSTAT_KEY = "geostat"
GEOSTAT_SCALAR_FIELDS = ("vario_loglog_slope", "isotropy")
GEOSTAT_COMPOSITION_FIELDS = (
    "curv_planar", "curv_peak", "curv_pit",
    "curv_ridge", "curv_channel", "curv_pass",
)
GEOSTAT_FIELDS = GEOSTAT_SCALAR_FIELDS + GEOSTAT_COMPOSITION_FIELDS

# Documented reference spans for the two scalar geostat sub-distances: on each axis a
# difference of this many native units is treated as a "full" (==1) separation, so the
# per-scalar sub-distance is ``min(1, |a - b| / span)`` and the averaged geostat term
# stays bounded in ``[0, 1]`` (the six composition fractions are instead compared with
# the total-variation distance ``0.5 * sum|a - b|``, already in ``[0, 1]``, exactly like
# the landform geomorphon-spectrum term):
#   * ``vario_loglog_slope`` -- the slope of log(gamma) vs log(h) over the rising part
#     of the semivariogram. For a self-affine surface gamma(h) ~ h^(2H) with the Hurst
#     exponent H in [0, 1], so the slope spans [0, 2]; a span of 2.0 is its full
#     physical range. dx-invariant (a constant rescaling of the lag shifts log(h) by a
#     constant and leaves the slope unchanged);
#   * ``isotropy``           -- Woodcock 3*lambda3, already a normalised [0, 1]
#     orientation-isotropy index (1 = perfectly isotropic normals), so its full range
#     is 1.0.
GEOSTAT_SPANS = {
    "vario_loglog_slope": 2.0,
    "isotropy": 1.0,
}


def _scale_fabric_signature(spec, aniso):
    """Build the flat scale/fabric ``{field: float}`` dict from a spectral and an
    anisotropy signature (as returned by
    :func:`terratrace.spectral.spectral_signature` /
    :func:`terratrace.anisotropy.anisotropy_signature`).

    The three per-band RMS values are turned into RATIOS of their sum so the
    stored fabric is a scale-free wavelength shape; if the bands sum to zero (a
    perfectly flat tile) the three ratios are ``nan``. Returns plain floats in
    :data:`SCALE_FABRIC_FIELDS` order.
    """
    bands = [float(spec["rough_long"]), float(spec["rough_mid"]),
             float(spec["rough_short"])]
    total = sum(bands)
    if np.isfinite(total) and total > 0.0:
        ratios = [b / total for b in bands]
    else:
        ratios = [float("nan")] * 3
    return {
        "spectral_slope": float(spec["spectral_slope"]),
        "rough_long_ratio": float(ratios[0]),
        "rough_mid_ratio": float(ratios[1]),
        "rough_short_ratio": float(ratios[2]),
        "anisotropy_strength": float(aniso["strength"]),
    }


def _scale_fabric_from_z(z, dx=1.0):
    """Scale/fabric dict for a raw elevation array, scanned on the fly.

    Calls the two source signatures directly (cheaper than a full descriptor
    bank). The stored fields are dx-invariant, so the module default ``dx=1.0``
    reproduces the same values the descriptor bank stores at any ``dx``.
    """
    z = np.asarray(z, dtype=float)
    return _scale_fabric_signature(spectral.spectral_signature(z, dx=dx),
                                   anisotropy.anisotropy_signature(z, dx=dx))


def _scale_fabric(fp_or_z, dx=1.0):
    """Resolve a scale/fabric ``{field: float}`` dict for a fingerprint or tile.

    A fingerprint dict must carry a :data:`SCALE_FABRIC_KEY` entry (build it with
    ``terrain_fingerprint(..., include_scale_fabric=True)``); a raw elevation
    array is scanned on the fly with :func:`_scale_fabric_from_z`. Returns a
    plain ``{field: float}`` dict in :data:`SCALE_FABRIC_FIELDS` order.
    """
    if isinstance(fp_or_z, dict):
        if SCALE_FABRIC_KEY not in fp_or_z:
            raise ValueError(
                "fingerprint has no %r; build it with "
                "terrain_fingerprint(..., include_scale_fabric=True) before "
                "using the scale/fabric similarity term" % SCALE_FABRIC_KEY)
        sf = fp_or_z[SCALE_FABRIC_KEY]
        return {k: float(sf[k]) for k in SCALE_FABRIC_FIELDS}
    return _scale_fabric_from_z(fp_or_z, dx=dx)


def scale_fabric_distance(a, b):
    """Bounded ``[0, 1]`` distance between two scale/fabric dicts.

    The scale/fabric term of :func:`similarity`. ``a`` and ``b`` are dicts over
    :data:`SCALE_FABRIC_FIELDS` (plain floats). The distance is the mean of three
    bounded, complementary sub-distances, each in ``[0, 1]``:

    * **slope** -- ``min(1, |slope_a - slope_b| / SCALE_FABRIC_SLOPE_SPAN)``
      (log-log spectral slope, normalised by :data:`SCALE_FABRIC_SLOPE_SPAN`);
    * **bands** -- the total-variation distance ``0.5 * sum|r_a - r_b|`` between
      the two 3-band roughness-ratio distributions (each sums to ~1), in
      ``[0, 1]``;
    * **fabric** -- ``min(1, |strength_a - strength_b|)`` (anisotropy strength,
      already in ``[0, 1]``).

    Any sub-distance that is non-finite (e.g. a degenerate tile whose spectral
    slope or band ratios are ``nan``) is dropped, and the mean is taken over the
    sub-distances that remain, so the term stays on the same ``[0, 1]`` footing
    regardless of how many were available. If NONE are finite the distance is
    ``0.0`` (no information -> no penalty), keeping :func:`similarity` finite.
    Returns a plain ``float``.
    """
    subs = []

    sa, sb = float(a["spectral_slope"]), float(b["spectral_slope"])
    if np.isfinite(sa) and np.isfinite(sb):
        subs.append(min(1.0, abs(sa - sb) / float(SCALE_FABRIC_SLOPE_SPAN)))

    ra = np.array([a["rough_long_ratio"], a["rough_mid_ratio"],
                   a["rough_short_ratio"]], dtype=float)
    rb = np.array([b["rough_long_ratio"], b["rough_mid_ratio"],
                   b["rough_short_ratio"]], dtype=float)
    if np.isfinite(ra).all() and np.isfinite(rb).all():
        subs.append(0.5 * float(np.abs(ra - rb).sum()))

    aa, ab = float(a["anisotropy_strength"]), float(b["anisotropy_strength"])
    if np.isfinite(aa) and np.isfinite(ab):
        subs.append(min(1.0, abs(aa - ab)))

    return float(np.mean(subs)) if subs else 0.0


def _texture_signature(z, dx=1.0):
    """Build the flat texture ``{field: float}`` dict for a raw elevation array.

    Collects four complementary map-scale TEXTURE / surface-complexity scalars by
    calling their source modules directly (lazily imported so this module's
    default import surface is unchanged): the log-log spectral slope
    (:func:`terratrace.spectral.spectral_signature`), the differential
    box-counting fractal dimension
    (:func:`terratrace.fractal.box_counting_dimension`), the normalised slope
    entropy (:func:`terratrace.entropy_terrain.entropy_signature`) and the r=2
    gliding-box lacunarity (:func:`terratrace.lacunarity.lacunarity_signature`).
    ``dx`` is forwarded to the two spacing-dependent signatures (the fractal
    dimension and the lacunarity are dx-free). Returns plain floats in
    :data:`TEXTURE_FIELDS` order (``nan`` where a source scalar is undefined, e.g.
    the spectral slope or lacunarity of a degenerate tile).
    """
    from . import fractal, entropy_terrain, lacunarity
    za = np.asarray(z, dtype=float)
    spec = spectral.spectral_signature(za, dx=dx)
    ent = entropy_terrain.entropy_signature(za, dx=dx)
    lac = lacunarity.lacunarity_signature(za)
    return {
        "spectral_slope": float(spec["spectral_slope"]),
        "fractal_dim": float(fractal.box_counting_dimension(za)),
        "slope_entropy_norm": float(ent["slope_entropy_norm"]),
        "lacunarity_r2": float(lac["lacunarity_r2"]),
    }


def _texture(fp_or_z, dx=1.0):
    """Resolve a texture ``{field: float}`` dict for a fingerprint or tile.

    A fingerprint dict must carry a :data:`TEXTURE_KEY` entry (build it with
    ``terrain_fingerprint(..., include_texture=True)``); a raw elevation array is
    scanned on the fly with :func:`_texture_signature`. Returns a plain
    ``{field: float}`` dict in :data:`TEXTURE_FIELDS` order.
    """
    if isinstance(fp_or_z, dict):
        if TEXTURE_KEY not in fp_or_z:
            raise ValueError(
                "fingerprint has no %r; build it with "
                "terrain_fingerprint(..., include_texture=True) before "
                "using the texture similarity term" % TEXTURE_KEY)
        tx = fp_or_z[TEXTURE_KEY]
        return {k: float(tx[k]) for k in TEXTURE_FIELDS}
    return _texture_signature(fp_or_z, dx=dx)


def texture_distance(a, b):
    """Bounded ``[0, 1]`` distance between two texture dicts.

    The texture term of :func:`similarity`. ``a`` and ``b`` are dicts over
    :data:`TEXTURE_FIELDS` (plain floats). For each field the sub-distance is
    ``min(1, |a - b| / TEXTURE_SPANS[field])`` -- the native-unit difference
    normalised by that axis's documented span (:data:`TEXTURE_SPANS`) so the four
    very differently-scaled scalars are commensurate -- and the distance is the
    mean of those sub-distances, so it stays in ``[0, 1]``.

    Any sub-distance that is non-finite (e.g. a degenerate tile whose spectral
    slope or lacunarity is ``nan``) is dropped, and the mean is taken over the
    sub-distances that remain, so the term stays on the same ``[0, 1]`` footing
    regardless of how many were available. If NONE are finite the distance is
    ``0.0`` (no information -> no penalty), keeping :func:`similarity` finite.
    Returns a plain ``float``.
    """
    subs = []
    for field in TEXTURE_FIELDS:
        va, vb = float(a[field]), float(b[field])
        span = float(TEXTURE_SPANS[field])
        if np.isfinite(va) and np.isfinite(vb) and span > 0.0:
            subs.append(min(1.0, abs(va - vb) / span))
    return float(np.mean(subs)) if subs else 0.0


def _geostat_signature(z, dx=1.0):
    """Build the flat geostat ``{field: float}`` dict for a raw elevation array.

    Collects a scale-aware geostatistical-structure summary by calling three source
    modules directly (lazily imported so this module's default import surface is
    unchanged): the variogram log-log roughness-scaling slope
    (:func:`terratrace.variogram.variogram_signature`), the surface-normal fabric
    isotropy (:func:`terratrace.fabric_eigen.fabric_signature`) and the six Wood (1996)
    curvature-feature area fractions
    (:func:`terratrace.curvature_classes.curvature_class_signature`). ``dx`` is
    forwarded to all three. Returns plain floats in :data:`GEOSTAT_FIELDS` order: the
    two scalars (``nan`` where a source scalar is undefined, e.g. the variogram slope of
    a degenerate flat tile) and the six ``curv_<class>`` composition fractions in
    :data:`terratrace.curvature_classes.CLASS_NAMES` order (always finite, summing to
    ~1 over classified cells).
    """
    from . import variogram, fabric_eigen, curvature_classes
    za = np.asarray(z, dtype=float)
    vs = variogram.variogram_signature(za, dx=dx)
    fs = fabric_eigen.fabric_signature(za, dx=dx)
    comp = curvature_classes.curvature_class_signature(za, dx=dx)["composition"]
    out = {
        "vario_loglog_slope": float(vs["vario_loglog_slope"]),
        "isotropy": float(fs["isotropy"]),
    }
    for name in curvature_classes.CLASS_NAMES:
        out["curv_" + name] = float(comp[name])
    return out


def _geostat(fp_or_z, dx=1.0):
    """Resolve a geostat ``{field: float}`` dict for a fingerprint or tile.

    A fingerprint dict must carry a :data:`GEOSTAT_KEY` entry (build it with
    ``terrain_fingerprint(..., include_geostat=True)``); a raw elevation array is
    scanned on the fly with :func:`_geostat_signature`. Returns a plain
    ``{field: float}`` dict in :data:`GEOSTAT_FIELDS` order.
    """
    if isinstance(fp_or_z, dict):
        if GEOSTAT_KEY not in fp_or_z:
            raise ValueError(
                "fingerprint has no %r; build it with "
                "terrain_fingerprint(..., include_geostat=True) before "
                "using the geostatistical similarity term" % GEOSTAT_KEY)
        gs = fp_or_z[GEOSTAT_KEY]
        return {k: float(gs[k]) for k in GEOSTAT_FIELDS}
    return _geostat_signature(fp_or_z, dx=dx)


def geostat_distance(a, b):
    """Bounded ``[0, 1]`` distance between two geostat dicts.

    The geostat term of :func:`similarity`. ``a`` and ``b`` are dicts over
    :data:`GEOSTAT_FIELDS` (plain floats). The distance is the mean of up to three
    bounded, complementary sub-distances, each in ``[0, 1]``:

    * for each scalar in :data:`GEOSTAT_SCALAR_FIELDS` the native-unit difference
      normalised by its documented span, ``min(1, |a - b| / GEOSTAT_SPANS[field])``
      (so the two differently-scaled scalars are commensurate);
    * the total-variation distance ``0.5 * sum|a - b|`` between the two six-class
      curvature-feature compositions (each sums to ~1), in ``[0, 1]`` -- exactly the
      metric the landform geomorphon-spectrum term uses.

    Any sub-distance that is non-finite (e.g. a degenerate tile whose variogram slope
    is ``nan``, or a composition that is not finite) is dropped, and the mean is taken
    over the sub-distances that remain, so the term stays on the same ``[0, 1]`` footing
    regardless of how many were available. If NONE are finite the distance is ``0.0``
    (no information -> no penalty), keeping :func:`similarity` finite. Returns a plain
    ``float``.
    """
    subs = []
    for field in GEOSTAT_SCALAR_FIELDS:
        va, vb = float(a[field]), float(b[field])
        span = float(GEOSTAT_SPANS[field])
        if np.isfinite(va) and np.isfinite(vb) and span > 0.0:
            subs.append(min(1.0, abs(va - vb) / span))
    ca = np.array([a[f] for f in GEOSTAT_COMPOSITION_FIELDS], dtype=float)
    cb = np.array([b[f] for f in GEOSTAT_COMPOSITION_FIELDS], dtype=float)
    if np.isfinite(ca).all() and np.isfinite(cb).all():
        subs.append(0.5 * float(np.abs(ca - cb).sum()))
    return float(np.mean(subs)) if subs else 0.0


def spectrum_tv(a, b):
    """Total-variation distance between two normalised geomorphon spectra.

    ``a`` and ``b`` are 9x9 normalised geomorphon spectra (nested lists or
    arrays, each summing to ~1 over valid cells). Returns the total-variation
    distance

        tv(a, b) = 0.5 * sum_ij |a_ij - b_ij|

    as a plain ``float`` in ``[0, 1]`` -- 0 iff the spectra are identical, 1 for
    fully disjoint supports. Map-scale morphology only; the landform term of
    :func:`similarity` uses exactly this metric.
    """
    return 0.5 * float(np.abs(np.asarray(a) - np.asarray(b)).sum())


def _landform_spectrum(fp_or_z, search=10, skip=0, flat_deg=1.0):
    """Resolve a 9x9 geomorphon spectrum array for a fingerprint dict or raw tile.

    A fingerprint dict must carry a :data:`LANDFORM_SPECTRUM_KEY` entry (build it
    with ``terrain_fingerprint(..., include_landform=True)``); a raw elevation
    array is scanned on the fly with :func:`terratrace.geomorphons.spectrum`
    under the given geomorphon parameters (and the module's ``dx=1.0`` default,
    matching the morphology distance's unit-spacing assumption). Returns a
    ``float`` ndarray of shape ``(9, 9)``.
    """
    if isinstance(fp_or_z, dict):
        if LANDFORM_SPECTRUM_KEY not in fp_or_z:
            raise ValueError(
                "fingerprint has no %r; build it with "
                "terrain_fingerprint(..., include_landform=True) before using "
                "the landform similarity term" % LANDFORM_SPECTRUM_KEY)
        return np.asarray(fp_or_z[LANDFORM_SPECTRUM_KEY], dtype=float)
    return geomorphons.spectrum(np.asarray(fp_or_z, dtype=float),
                                search=search, skip=skip, flat_deg=flat_deg)


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


def terrain_fingerprint(z, dx=1.0, window=5, include_landform=False,
                        search=10, skip=0, flat_deg=1.0,
                        include_scale_fabric=False, include_texture=False,
                        include_geostat=False):
    """Compute the morphological fingerprint of one elevation tile.

    Runs :func:`descriptors.descriptor_bank` once and pulls the fixed subset
    named by :data:`FINGERPRINT_FIELDS` into an insertion-ordered
    ``{field_name: float}`` dict (same order as FINGERPRINT_FIELDS). Every
    value is a plain ``float`` -- ``nan`` where a descriptor is undefined
    (e.g. the Hurst exponent or hypsometric integral of a perfectly flat
    tile) -- so the result is JSON-serialisable and deterministic for a given
    array. Map-scale morphology only; see the module docstring.

    When ``include_landform`` is True an ADDITIVE
    :data:`LANDFORM_SPECTRUM_KEY` entry is added holding the normalised 9x9
    geomorphon spectrum (:func:`terratrace.geomorphons.spectrum`) as a nested
    list of floats; ``search`` / ``skip`` / ``flat_deg`` are its geomorphon
    parameters. This is the landform component consumed by the OPT-IN landform
    term of :func:`similarity`.

    When ``include_scale_fabric`` is True a second ADDITIVE
    :data:`SCALE_FABRIC_KEY` entry is added holding the flat scale/fabric dict
    over :data:`SCALE_FABRIC_FIELDS` (spectral slope, the three roughness-band
    ratios, and the anisotropy strength), derived from the bank's ``"spectral"``
    and ``"anisotropy"`` blocks. This is the component consumed by the OPT-IN
    scale/fabric term of :func:`similarity`.

    When ``include_texture`` is True a third ADDITIVE :data:`TEXTURE_KEY` entry is
    added holding the flat texture dict over :data:`TEXTURE_FIELDS` -- the
    ``spectral_slope`` (:func:`terratrace.spectral.spectral_signature`),
    ``fractal_dim`` (:func:`terratrace.fractal.box_counting_dimension`),
    ``slope_entropy_norm`` (:func:`terratrace.entropy_terrain.entropy_signature`)
    and ``lacunarity_r2`` (:func:`terratrace.lacunarity.lacunarity_signature`), as
    plain floats. This is the component consumed by the OPT-IN texture term of
    :func:`similarity`.

    When ``include_geostat`` is True a fourth ADDITIVE :data:`GEOSTAT_KEY` entry is
    added holding the flat geostat dict over :data:`GEOSTAT_FIELDS` -- the variogram
    log-log roughness-scaling slope
    (:func:`terratrace.variogram.variogram_signature`), the surface-normal fabric
    ``isotropy`` (:func:`terratrace.fabric_eigen.fabric_signature`) and the six
    ``curv_<class>`` Wood (1996) curvature-feature area fractions
    (:func:`terratrace.curvature_classes.curvature_class_signature`), as plain floats.
    This is the component consumed by the OPT-IN geostat term of :func:`similarity`.

    All optional entries are purely additive: the FINGERPRINT_FIELDS scalars
    are left untouched, so by default (all flags False) the fingerprint is
    byte-identical to one built before these components existed and existing
    callers / tests are unchanged.
    """
    bank = descriptors.descriptor_bank(z, dx=dx, window=window)
    fp = {field: _pull(bank, field) for field in FINGERPRINT_FIELDS}
    if include_landform:
        fp[LANDFORM_SPECTRUM_KEY] = geomorphons.spectrum(
            np.asarray(z, dtype=float), dx=dx, search=search, skip=skip,
            flat_deg=flat_deg).tolist()
    if include_scale_fabric:
        fp[SCALE_FABRIC_KEY] = _scale_fabric_signature(bank["spectral"],
                                                       bank["anisotropy"])
    if include_texture:
        fp[TEXTURE_KEY] = _texture_signature(np.asarray(z, dtype=float), dx=dx)
    if include_geostat:
        fp[GEOSTAT_KEY] = _geostat_signature(np.asarray(z, dtype=float), dx=dx)
    return fp


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


def _morph_distance(fp_a, fp_b, scales=None):
    """Per-dimension-normalised RMS distance over FINGERPRINT_FIELDS.

    The morphology distance underlying :func:`similarity` (see that function's
    docstring for the full definition and the pairwise-complete handling).
    Returns a plain ``float``, or ``nan`` when no dimension is
    pairwise-complete.
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
    return float(np.sqrt(np.mean(diff ** 2)))


def similarity(fp_a, fp_b, scales=None, include_landform=False, landform_weight=1.0,
               include_scale_fabric=False, scale_fabric_weight=1.0,
               include_texture=False, texture_weight=1.0,
               include_geostat=False, geostat_weight=1.0):
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

    OPT-IN landform term: with ``include_landform=True`` a weighted
    total-variation distance between the two tiles' normalised 9x9 geomorphon
    spectra is ADDED to ``d`` before the ``1 / (1 + d)`` map::

        d_total = d_morph + landform_weight * spectrum_tv(spec_a, spec_b)

    using :func:`spectrum_tv` (range ``[0, 1]``). The spectra come from each
    argument via :func:`_landform_spectrum`: a fingerprint dict must have been
    built with ``terrain_fingerprint(..., include_landform=True)`` (else a
    ``ValueError`` is raised), while a raw array is scanned on the fly. When
    the morphology distance is itself ``nan`` (no comparable dimension) only
    the landform term contributes. ``include_landform=False`` (the default) is
    byte-identical to the morphology-only behaviour, so existing callers are
    unchanged unless they opt in.

    OPT-IN scale/fabric term: with ``include_scale_fabric=True`` a weighted
    scale/fabric distance is likewise ADDED to ``d``::

        d_total += scale_fabric_weight * scale_fabric_distance(sf_a, sf_b)

    using :func:`scale_fabric_distance` (range ``[0, 1]``) over the two tiles'
    scale/fabric dicts (spectral slope, roughness-band ratios, anisotropy
    strength). Each dict comes from its argument via :func:`_scale_fabric`: a
    fingerprint dict must have been built with
    ``terrain_fingerprint(..., include_scale_fabric=True)`` (else a
    ``ValueError`` is raised), while a raw array is scanned on the fly.

    OPT-IN texture term: with ``include_texture=True`` a weighted texture
    distance is likewise ADDED to ``d``::

        d_total += texture_weight * texture_distance(tex_a, tex_b)

    using :func:`texture_distance` (range ``[0, 1]``) over the two tiles' texture
    dicts (spectral slope, box-counting fractal dimension, normalised slope
    entropy, r=2 lacunarity), each sub-distance normalised by its documented
    :data:`TEXTURE_SPANS` entry. Each dict comes from its argument via
    :func:`_texture`: a fingerprint dict must have been built with
    ``terrain_fingerprint(..., include_texture=True)`` (else a ``ValueError`` is
    raised), while a raw array is scanned on the fly.

    OPT-IN geostat term: with ``include_geostat=True`` a weighted geostatistical
    distance is likewise ADDED to ``d``::

        d_total += geostat_weight * geostat_distance(gs_a, gs_b)

    using :func:`geostat_distance` (range ``[0, 1]``) over the two tiles' geostat
    dicts -- the variogram log-log roughness-scaling slope and the surface-normal
    fabric isotropy (each span-normalised by its :data:`GEOSTAT_SPANS` entry) plus the
    total-variation distance between the two six-class curvature-feature compositions.
    Each dict comes from its argument via :func:`_geostat`: a fingerprint dict must
    have been built with ``terrain_fingerprint(..., include_geostat=True)`` (else a
    ``ValueError`` is raised), while a raw array is scanned on the fly. The four opt-in
    terms are independent and may be combined; with all flags False the behaviour is
    byte-identical to the morphology-only similarity.
    """
    d = _morph_distance(fp_a, fp_b, scales=scales)
    if include_landform:
        tv = spectrum_tv(_landform_spectrum(fp_a), _landform_spectrum(fp_b))
        d = (0.0 if not np.isfinite(d) else d) + float(landform_weight) * tv
    if include_scale_fabric:
        sf = scale_fabric_distance(_scale_fabric(fp_a), _scale_fabric(fp_b))
        d = (0.0 if not np.isfinite(d) else d) + float(scale_fabric_weight) * sf
    if include_texture:
        tx = texture_distance(_texture(fp_a), _texture(fp_b))
        d = (0.0 if not np.isfinite(d) else d) + float(texture_weight) * tx
    if include_geostat:
        gs = geostat_distance(_geostat(fp_a), _geostat(fp_b))
        d = (0.0 if not np.isfinite(d) else d) + float(geostat_weight) * gs
    if not np.isfinite(d):
        return float("nan")
    return 1.0 / (1.0 + d)


def rank_library(query, library, scales=None, include_landform=False,
                 landform_weight=1.0, include_scale_fabric=False,
                 scale_fabric_weight=1.0, include_texture=False,
                 texture_weight=1.0, include_geostat=False, geostat_weight=1.0):
    """Rank reference terrains by morphological similarity to ``query``.

    ``query`` is a fingerprint dict or a raw elevation array; ``library`` is a
    ``{name: fingerprint-or-array}`` mapping. Returns a list of
    ``(name, similarity)`` sorted by similarity DESCENDING -- the best
    morphological match first -- with ties broken by ``name`` ascending and
    ``nan`` similarities (no comparable dimension) sorted last. ``scales`` is
    forwarded to :func:`similarity`; the query fingerprint is computed once.
    Morphological resemblance only; not a classification or identity claim.

    ``include_landform`` / ``landform_weight``, ``include_scale_fabric`` /
    ``scale_fabric_weight``, ``include_texture`` / ``texture_weight`` and
    ``include_geostat`` / ``geostat_weight`` are forwarded to :func:`similarity` to add
    the opt-in landform, scale/fabric, texture and geostat terms. When any is enabled
    and ``query`` is a raw array it is fingerprinted WITH the matching component, and
    every library entry must likewise expose that component (a raw array, or a dict
    built with the corresponding ``include_*`` flag) or a ``ValueError`` is raised.
    Defaults (all flags False) preserve the existing behaviour exactly.
    """
    q = (query if isinstance(query, dict)
         else terrain_fingerprint(query, include_landform=include_landform,
                                  include_scale_fabric=include_scale_fabric,
                                  include_texture=include_texture,
                                  include_geostat=include_geostat))
    ranked = [(name, similarity(q, ref, scales=scales,
                                include_landform=include_landform,
                                landform_weight=landform_weight,
                                include_scale_fabric=include_scale_fabric,
                                scale_fabric_weight=scale_fabric_weight,
                                include_texture=include_texture,
                                texture_weight=texture_weight,
                                include_geostat=include_geostat,
                                geostat_weight=geostat_weight))
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
