"""Source-resolution matching -- equalise EFFECTIVE resolution before comparison.

WHY THIS EXISTS (the scientific defect it corrects). Two DEMs can be aggregated to
the same support and still not resolve the same scales. Mars MOLA is gridded at
463 m, but much of that grid is interpolated between laser tracks, so its true
resolving power is roughly 3x coarser (~1.4 km); Copernicus GLO-30 is posted at
30 m (effective ~90 m). At a common support finer than ~1.4 km the Mars grid looks
ARTIFICIALLY SMOOTH (interpolation) while the Earth grid keeps genuine short-
wavelength detail. That asymmetry can make the smoothest Earth candidate look like
the best "analog" for reasons that have nothing to do with terrain -- a source-
smoothing artifact, not morphology.

THE CONTROL. Every finer-resolution unit is low-passed with a Gaussian to the
COARSEST unit's effective resolution before comparison, so all sources resolve the
same scales. Gaussian point-spread functions add in quadrature, so a unit whose own
effective resolution is ``own`` (expressed as a Gaussian FWHM) reaches a target
FWHM ``target`` with a kernel of FWHM ``sqrt(target^2 - own^2)``. A unit that is
already coarser than (or equal to) the target is left untouched -- it is never
sharpened. If an analog survives this control, it is not a smoothing artifact.

The filter is a NaN-safe normalised convolution (Knutsson & Westin 1993):
``smooth(z*w) / smooth(w)`` with ``w`` the finite-data mask, so nodata does not
bleed in and borders are not darkened or biased. It is computed by FFT on a
zero-padded grid (pad >= 4 sigma on every side) -- an exact LINEAR convolution with
a truncated, unit-sum Gaussian, so there is no wrap-around. Pure NumPy, no SciPy;
deterministic; ~1500 x 1500 at sigma ~25 px runs well under a second.

Scientific boundary / claim firewall: this EQUALISES effective resolution; it does
NOT add information -- the finer source is degraded to the coarser one, never the
reverse, and nothing below the coarsest source's resolving power is recovered. The
``res_factor * spacing`` effective-resolution figure (default 3x, shared with
:func:`terratrace.matched_benchmark.effective_resolution_m`) is a conservative
HEURISTIC, not a measured modulation-transfer function of any instrument or
gridding process; treating it as a Gaussian FWHM is a modelling convention. The
output feeds map-scale terrain-MORPHOLOGY screening only -- no traversability,
hazard, geologic-equivalence, site-access, or mission-readiness claim is made on
Mars, Earth, or any other body.
"""
from __future__ import annotations

import math

import numpy as np

from .matched_benchmark import effective_resolution_m

__all__ = [
    "fwhm_to_sigma",
    "gaussian_filter_nan",
    "emulate_effective_resolution",
    "match_effective_resolution",
]

_FWHM_PER_SIGMA = 2.0 * math.sqrt(2.0 * math.log(2.0))   # ~2.3548
_TRUNCATE = 4.0                                            # kernel radius, in sigmas


def fwhm_to_sigma(fwhm):
    """Gaussian standard deviation for a full width at half maximum:
    ``sigma = fwhm / (2 * sqrt(2 * ln 2))`` (same units as ``fwhm``)."""
    return float(fwhm) / _FWHM_PER_SIGMA


def _good_size(n):
    """Smallest 5-smooth integer (2^a 3^b 5^c) >= n -- a fast FFT length."""
    n = max(int(n), 1)
    best = None
    p5 = 1
    while p5 < 2 * n:
        p35 = p5
        while p35 < 2 * n:
            p = p35
            while p < n:
                p *= 2
            if best is None or p < best:
                best = p
            p35 *= 3
        p5 *= 5
    return best


def _kernel_1d(sigma, radius):
    """Sampled Gaussian on [-radius, radius], normalised to unit sum."""
    x = np.arange(-radius, radius + 1, dtype=float)
    g = np.exp(-0.5 * (x / sigma) ** 2)
    return g / g.sum()


def _wrapped_kernel(g, radius, m):
    """Place a centred 1-D kernel at index 0 of a length-``m`` circular buffer."""
    k = np.zeros(m, dtype=float)
    k[:radius + 1] = g[radius:]
    if radius:
        k[-radius:] = g[:radius]
    return k


def gaussian_filter_nan(z, sigma_px):
    """NaN-safe Gaussian low-pass by normalised convolution.

    Returns ``smooth(z_filled * w) / smooth(w)`` where ``w`` is the finite mask and
    ``z_filled`` is ``z`` with non-finite cells set to 0; cells that were non-finite
    in the input are NaN in the output. The Gaussian (std ``sigma_px`` pixels) is
    truncated at 4 sigma and renormalised; the convolution is done by real FFT on a
    grid zero-padded by the kernel radius (>= 4 sigma) on every side, so it is an
    exact linear convolution with NO wrap-around. Edges are handled by the
    normalisation (a constant field stays constant up to the border). ``sigma_px <=
    0`` returns a float copy unchanged. The input is never mutated.
    """
    z = np.array(z, dtype=float, copy=True)
    if z.ndim != 2:
        raise ValueError("gaussian_filter_nan expects a 2-D array")
    sigma = float(sigma_px)
    if not math.isfinite(sigma):
        raise ValueError("sigma_px must be finite")
    if sigma <= 0.0 or z.size == 0:
        return z
    w = np.isfinite(z)
    if not w.any():
        return np.full(z.shape, np.nan)
    n0, n1 = z.shape
    radius = max(int(math.ceil(_TRUNCATE * sigma)), 1)
    m0, m1 = _good_size(n0 + 2 * radius), _good_size(n1 + 2 * radius)
    g = _kernel_1d(sigma, radius)
    k0 = np.fft.fft(_wrapped_kernel(g, radius, m0))
    k1 = np.fft.rfft(_wrapped_kernel(g, radius, m1))
    kernel_hat = k0[:, None] * k1[None, :]

    stack = np.zeros((2, m0, m1), dtype=float)
    stack[0, radius:radius + n0, radius:radius + n1] = np.where(w, z, 0.0)
    stack[1, radius:radius + n0, radius:radius + n1] = w
    out = np.fft.irfft2(np.fft.rfft2(stack, axes=(-2, -1)) * kernel_hat,
                        s=(m0, m1), axes=(-2, -1))
    num = out[0, radius:radius + n0, radius:radius + n1]
    den = out[1, radius:radius + n0, radius:radius + n1]
    # A finite cell always carries its own centre weight (g[0]^2 > 0), so den is
    # bounded well away from 0 there; the guard only absorbs FFT round-off.
    good = w & (den > 1e-12)
    res = np.full(z.shape, np.nan)
    res[good] = num[good] / den[good]
    return res


def emulate_effective_resolution(z, spacing_m, target_fwhm_m, own_fwhm_m=None,
                                 res_factor=3.0):
    """Degrade ``z`` (posted at ``spacing_m``) to a coarser effective resolution.

    ``own_fwhm_m`` defaults to ``effective_resolution_m(spacing_m, res_factor)``
    (the 3x-spacing heuristic). The Gaussian kernel FWHM is
    ``sqrt(target^2 - own^2)`` (quadrature addition of Gaussian PSFs). If
    ``target_fwhm_m <= own_fwhm_m`` the grid is already at least that coarse and
    an unchanged float copy is returned with ``smoothed=False`` -- never sharpened.

    Returns ``(z_out, info)`` with ``info = {own_fwhm_m, target_fwhm_m,
    kernel_fwhm_m, sigma_px, smoothed}`` (plain floats/bool; JSON-serialisable).
    """
    spacing = float(spacing_m)
    if not (math.isfinite(spacing) and spacing > 0.0):
        raise ValueError("spacing_m must be a positive finite number")
    own = (effective_resolution_m(spacing, res_factor) if own_fwhm_m is None
           else float(own_fwhm_m))
    target = float(target_fwhm_m)
    if not (target > own):
        info = {"own_fwhm_m": own, "target_fwhm_m": target, "kernel_fwhm_m": 0.0,
                "sigma_px": 0.0, "smoothed": False}
        return np.array(z, dtype=float, copy=True), info
    kernel_fwhm = math.sqrt(target * target - own * own)
    sigma_px = fwhm_to_sigma(kernel_fwhm) / spacing
    info = {"own_fwhm_m": own, "target_fwhm_m": target,
            "kernel_fwhm_m": float(kernel_fwhm), "sigma_px": float(sigma_px),
            "smoothed": True}
    return gaussian_filter_nan(z, sigma_px), info


def match_effective_resolution(grids, spacings, res_factor=3.0, target_fwhm_m=None):
    """Bring every unit to a common EFFECTIVE resolution before comparison.

    ``grids`` is ``{unit_id: 2-D elevation array}``; ``spacings`` is a scalar or
    ``{unit_id: metres}``. The target FWHM defaults to the COARSEST unit's
    effective resolution, ``max(effective_resolution_m(spacing, res_factor))``.
    Units at or coarser than the target are returned unchanged; finer units are
    Gaussian-smoothed to it (see :func:`emulate_effective_resolution`).

    Returns ``(grids_out, report)`` with ``report = {"target_fwhm_m": float,
    "units": {unit_id: info}}`` (JSON-serialisable). Inputs are never mutated;
    every output grid is a fresh float array. This equalises resolving power; it
    does not add information.
    """
    keys = list(grids)
    if isinstance(spacings, dict):
        sp = {k: float(spacings[k]) for k in keys}
    else:
        sp = {k: float(spacings) for k in keys}
    own = {k: effective_resolution_m(sp[k], res_factor) for k in keys}
    if target_fwhm_m is None:
        target = max(own.values()) if own else 0.0
    else:
        target = float(target_fwhm_m)
    out, units = {}, {}
    for k in keys:
        out[k], units[k] = emulate_effective_resolution(
            grids[k], sp[k], target, own_fwhm_m=own[k], res_factor=res_factor)
    return out, {"target_fwhm_m": float(target), "units": units}
