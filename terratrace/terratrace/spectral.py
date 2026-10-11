"""Radially-averaged 2-D power-spectral-density (PSD) roughness descriptor.

Turns an elevation grid into a radially-averaged power spectrum and a handful of
scalar roughness descriptors: the log-log spectral slope (how power is shared
between long and short wavelengths), the per-band RMS amplitude, the dominant
wavelength, and the total spectral power (which recovers the detrended variance
by Parseval). Pure NumPy (``numpy.fft``); no SciPy.

Pipeline (see ``radial_psd``): NaN cells are filled with the finite mean, a
least-squares best-fit plane ``a + b*x + c*y`` is removed so DC/tilt do not
dominate, a separable Hann window tapers the edges to curb spectral leakage, and
the windowed periodogram is normalised by the window energy ``sum(W**2)`` so the
spectrum integrates back to the detrended variance. The 2-D power is then
radially averaged over wavenumber ``kr = sqrt(kx**2 + ky**2)`` (cycles/metre),
excluding the k=0 (DC) bin.

Claim firewall: these are map-scale MORPHOLOGY / roughness-spectrum descriptors
of the sampled elevation grid ONLY. They summarise how spectral power is
distributed across spatial wavelengths. They are NOT a traversability, hazard,
trafficability, geologic, or mission/rover claim, and say nothing about rock-
scale obstacles below the pixel scale.
"""
from __future__ import annotations

import numpy as np


def _fill_nan_mean(z):
    """Return a copy of ``z`` with non-finite cells set to the finite mean
    (0.0 if nothing is finite). The documented NaN policy for the whole module."""
    z = np.array(z, dtype=float, copy=True)
    bad = ~np.isfinite(z)
    if bad.any():
        good = z[~bad]
        z[bad] = float(good.mean()) if good.size else 0.0
    return z


def detrend_plane(z):
    """Fill NaNs with the finite mean, then subtract the least-squares best-fit
    plane ``z = a + b*x + c*y`` (x=column index, y=row index). Returns the
    detrended, NaN-free grid (mean ~0). Exposed so callers/tests can reproduce
    the exact internal detrend used by the spectrum."""
    z = np.asarray(z, dtype=float)
    if z.ndim != 2:
        raise ValueError("spectral analysis needs a 2-D elevation grid")
    filled = _fill_nan_mean(z)
    nr, nc = filled.shape
    yy, xx = np.mgrid[0:nr, 0:nc]
    A = np.column_stack([np.ones(filled.size), xx.ravel().astype(float),
                         yy.ravel().astype(float)])
    coef, *_ = np.linalg.lstsq(A, filled.ravel(), rcond=None)
    return filled - (A @ coef).reshape(nr, nc)


def _hann2d(nr, nc):
    """Separable 2-D Hann window = outer product of 1-D Hann windows."""
    return np.outer(np.hanning(nr), np.hanning(nc))

def _radial_bin(z, dx, detrend, window):
    """Core pipeline. Returns ``(k_centers, psd_mean, power_per_bin)`` with the
    DC bin and empty bins removed. ``psd_mean`` is the mean power per mode in each
    annulus (a spectral density -> use for the slope); ``power_per_bin`` is the
    summed power in each annulus (-> use for variance/RMS, since the summed power
    over all annuli recovers the detrended variance by Parseval)."""
    d = detrend_plane(z) if detrend else _fill_nan_mean(z)
    nr, nc = d.shape
    W = _hann2d(nr, nc) if window else np.ones((nr, nc))
    g = d * W
    S = float(np.sum(W * W))
    N = nr * nc
    F = np.fft.fft2(g)
    P = (np.abs(F) ** 2) / (N * S)          # sum(P) ~= variance of d (Parseval)
    kx = np.fft.fftfreq(nc, d=dx)
    ky = np.fft.fftfreq(nr, d=dx)
    KX, KY = np.meshgrid(kx, ky)
    kr = np.sqrt(KX * KX + KY * KY).ravel()
    P = P.ravel()
    nbins = max(1, min(nr, nc) // 2)
    kmax = float(kr.max())
    if kmax <= 0.0:
        empty = np.empty(0)
        return empty, empty, empty
    edges = np.linspace(0.0, kmax, nbins + 1)
    idx = np.clip(np.digitize(kr, edges) - 1, 0, nbins - 1)
    power = np.bincount(idx, weights=P, minlength=nbins)
    counts = np.bincount(idx, minlength=nbins).astype(float)
    centers = 0.5 * (edges[:-1] + edges[1:])
    keep = counts > 0
    keep[0] = False                          # exclude the k=0 (DC) bin
    return centers[keep], power[keep] / counts[keep], power[keep]


def radial_psd(z, dx=1.0, detrend=True, window=True):
    """Radially-averaged 2-D PSD. Returns ``(k_cycles_per_m, psd)`` as equal-length
    ascending 1-D arrays with strictly positive k and finite psd (the DC bin is
    excluded). ``psd`` is the mean power per mode in each wavenumber annulus."""
    k, psd, _ = _radial_bin(z, dx, detrend, window)
    return k, psd

def _slope_from(k, psd, kmin, kmax):
    if k.size == 0:
        return float("nan")
    if kmin is None and kmax is None:
        n = k.size
        end = n - int(np.ceil(0.15 * n))     # drop the near-Nyquist tail
        kk, pp = k[1:end], psd[1:end]        # and the lowest-k bin
    else:
        lo = k.min() if kmin is None else kmin
        hi = k.max() if kmax is None else kmax
        m = (k >= lo) & (k <= hi)
        kk, pp = k[m], psd[m]
    good = np.isfinite(kk) & np.isfinite(pp) & (kk > 0) & (pp > 0)
    kk, pp = kk[good], pp[good]
    if kk.size < 3:
        return float("nan")
    return float(np.polyfit(np.log10(kk), np.log10(pp), 1)[0])


def spectral_slope(z, dx=1.0, kmin=None, kmax=None):
    """Least-squares slope of ``log10(psd)`` vs ``log10(k)`` over a mid-band that
    drops the lowest-k bin and the top ~15% of k (or ``[kmin, kmax]`` if given).
    Typically negative for terrain. Returns NaN if fewer than 3 usable bins."""
    k, psd, _ = _radial_bin(z, dx, True, True)
    return _slope_from(k, psd, kmin, kmax)


def _bands_from(k, power):
    out = {"long": 0.0, "mid": 0.0, "short": 0.0}
    if k.size == 0:
        return out
    lk = np.log10(k)
    lo, hi = float(lk.min()), float(lk.max())
    if hi <= lo:
        out["mid"] = float(np.sqrt(max(0.0, float(power.sum()))))
        return out
    e1, e2 = lo + (hi - lo) / 3.0, lo + 2.0 * (hi - lo) / 3.0
    masks = {"long": lk <= e1, "mid": (lk > e1) & (lk <= e2), "short": lk > e2}
    for key, m in masks.items():
        out[key] = float(np.sqrt(max(0.0, float(power[m].sum()))))
    return out


def band_roughness(z, dx=1.0):
    """RMS amplitude in three log-k wavelength bands: ``long`` (lowest third of
    log-k = longest wavelengths), ``mid``, ``short`` (highest third). Each value
    is ``sqrt(sum of per-bin power in the band)``."""
    k, _, power = _radial_bin(z, dx, True, True)
    return _bands_from(k, power)
def spectral_signature(z, dx=1.0):
    """JSON-serialisable dict of float descriptors: ``spectral_slope``,
    ``total_power`` (summed spectral power ~ detrended variance), ``roughness_rms``
    (std of the detrended grid), ``peak_wavelength_m`` (1/k at peak psd; NaN if
    degenerate), and the band RMS values ``rough_long``/``rough_mid``/``rough_short``."""
    d = detrend_plane(z)
    k, psd, power = _radial_bin(z, dx, True, True)
    slope = _slope_from(k, psd, None, None)
    bands = _bands_from(k, power)
    if psd.size and np.isfinite(psd).any() and float(np.nanmax(psd)) > 0.0:
        kp = k[int(np.nanargmax(psd))]
        peak_wl = float(1.0 / kp) if np.isfinite(kp) and kp > 0 else float("nan")
    else:
        peak_wl = float("nan")
    return {
        "spectral_slope": float(slope),
        "total_power": float(power.sum()) if power.size else 0.0,
        "roughness_rms": float(np.std(d)),
        "peak_wavelength_m": float(peak_wl),
        "rough_long": float(bands["long"]),
        "rough_mid": float(bands["mid"]),
        "rough_short": float(bands["short"]),
    }


