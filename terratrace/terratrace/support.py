"""Common-support aggregation.

Comparing terrain across sources requires representing both at a common
effective spatial support. This module degrades a finer grid to a coarser
analysis support by integer block aggregation and tracks the valid-data
fraction so missingness is never hidden.
"""
from __future__ import annotations

import warnings
from dataclasses import dataclass, asdict
import numpy as np


@dataclass
class SupportRecord:
    native_posting_m: float
    target_support_m: float
    factor: int
    valid_fraction: float
    aggregation: str

    def to_dict(self):
        return asdict(self)


def block_aggregate(z, factor, native_posting_m, aggregation="mean", min_valid=0.5):
    """Aggregate z by an integer factor using block reduction.

    Returns (aggregated_grid, SupportRecord). Blocks whose valid fraction
    is below min_valid become NaN. Partial edge blocks are trimmed.
    """
    if factor < 1:
        raise ValueError("factor must be >= 1")
    z = np.asarray(z, dtype=float)
    rows = (z.shape[0] // factor) * factor
    cols = (z.shape[1] // factor) * factor
    trimmed = z[:rows, :cols]
    blocks = trimmed.reshape(rows // factor, factor, cols // factor, factor)
    valid = ~np.isnan(blocks)
    valid_frac = valid.mean(axis=(1, 3))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        if aggregation == "mean":
            agg = np.nanmean(blocks, axis=(1, 3))
        elif aggregation == "median":
            agg = np.nanmedian(blocks, axis=(1, 3))
        else:
            raise ValueError(f"unknown aggregation {aggregation}")
    agg = np.where(valid_frac >= min_valid, agg, np.nan)
    overall_valid = float(np.isfinite(agg).mean()) if agg.size else 0.0
    record = SupportRecord(
        native_posting_m=float(native_posting_m),
        target_support_m=float(native_posting_m * factor),
        factor=int(factor),
        valid_fraction=overall_valid,
        aggregation=aggregation,
    )
    return agg, record


def common_factor(native_a_m, native_b_m, target_support_m):
    """Integer aggregation factors to bring two grids near a common support.

    Returns (factor_a, factor_b). Factors are at least 1.
    """
    for name, v in (("native_a_m", native_a_m), ("native_b_m", native_b_m),
                    ("target_support_m", target_support_m)):
        if not (v and v > 0):
            raise ValueError(f"{name} must be a positive number, got {v!r}")
    fa = max(int(round(target_support_m / native_a_m)), 1)
    fb = max(int(round(target_support_m / native_b_m)), 1)
    return fa, fb
