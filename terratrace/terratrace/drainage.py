"""Surface dissection texture via depression-filled D8 flow accumulation.

O'Callaghan, J. F., & Mark, D. M. (1984). The extraction of drainage networks
from digital elevation data. Computer Vision, Graphics, and Image Processing,
28(3), 323-344. [D8 single-flow-direction routing]

Barnes, R., Lehman, C., & Mulla, D. (2014). Priority-flood: An optimal
depression-filling and watershed-labeling algorithm for digital elevation
models. Computers & Geosciences, 62, 117-127. [priority-flood depression
filling + flow-direction assignment]

Horton, R. E. (1945). Erosional development of streams and their drainage
basins. Geological Society of America Bulletin, 56(3), 275-370. [drainage
density]

This module measures how the sampled surface would ROUTE a space-filling flow.
It fills the depressions of the elevation grid (priority flood), assigns a single
D8 downstream direction to every finite cell, accumulates the number of upstream
cells draining through each cell, and derives a compact *dissection-texture*
signature (channel fraction, mean log accumulation, peak concentration, a
drainage-density proxy).

Claim firewall -- READ THIS. Every quantity here is a PURELY GEOMETRIC descriptor
of how a gravity-driven, space-filling flow would traverse the sampled DEM. It is
NOT a claim of water, ice, precipitation, climate, fluvial activity, erosion, or
any surface process on Mars, the Moon, Mercury, Ceres, Earth, or any other body.
The words "flow", "drainage", "channel" and "density" are used in their abstract
graph-on-a-grid sense -- steepest-descent routing on a depression-filled height
field, exactly as a flow-accumulation operator is defined in geomorphometry.
Nothing here estimates traversability, hazard, habitability, resource presence,
or mission behaviour.

Algorithm. The depression fill is the priority flood of Barnes et al. (2014): a
min-heap is seeded with every border cell and every finite cell orthogonally
adjacent to nodata (the domain's outlets) and the surface is flooded outward in
ascending spill order, raising each interior cell to the highest spill level on
its lowest path to an outlet. Flow directions are assigned during the same flood
-- each cell drains to the already-processed cell it was first reached from --
yielding an acyclic drainage with no flat ambiguity in which every finite cell
routes, ultimately, to a domain-edge / nodata outlet. Accumulation is then a
single reverse pass over the flood order (upstream before downstream). The
eight-direction, single-flow (D8) convention follows O'Callaghan & Mark (1984).

Units: ``dx`` is the grid spacing in metres. Pure NumPy + the standard-library
``heapq``; NaN-safe (nodata cells are skipped and carry NaN accumulation);
deterministic and host-independent (an integer graph structure, exact for grids
up to a few hundred-thousand cells). No SciPy, no network, no disk.
"""
from __future__ import annotations

import heapq

import numpy as np

__all__ = [
    "fill_and_flowdirs",
    "fill_depressions",
    "d8_flow_direction",
    "flow_accumulation",
    "drainage_signature",
]

# The eight D8 neighbour offsets (di, dj), indexed 0..7 clockwise from north.
# Opposite directions are exactly 4 apart, so the direction pointing BACK from a
# neighbour reached via offset index ``d`` is ``(d + 4) % 8`` -- used to make a
# newly-flooded cell drain to the cell it was first reached from.
_NEIGHBORS = (
    (-1, 0),    # 0  N
    (-1, 1),    # 1  NE
    (0, 1),     # 2  E
    (1, 1),     # 3  SE
    (1, 0),     # 4  S
    (1, -1),    # 5  SW
    (0, -1),    # 6  W
    (-1, -1),   # 7  NW
)
_OPPOSITE = tuple((d + 4) % 8 for d in range(8))


def _as_grid(z):
    """Return ``z`` as a 2-D float64 array (a copy), validating its shape."""
    z = np.array(z, dtype=float, copy=True)
    if z.ndim != 2:
        raise ValueError("z must be a 2-D elevation grid")
    return z


def _flood(z):
    """Priority-flood depression fill + flow-direction assignment.

    Returns ``(filled, flowdir, order)``:

    * ``filled`` -- float64, the depression-filled surface (``>= z`` on finite
      cells; NaN preserved on nodata);
    * ``flowdir`` -- int8, the D8 direction index (0..7) each finite cell drains
      to -- the cell it was first reached from during the flood -- or ``-1`` for
      a domain-edge / nodata outlet and for every NaN cell;
    * ``order`` -- the list of finite ``(i, j)`` in heap-pop (ascending spill)
      order. A cell is pushed only when its downstream cell is popped, so
      REVERSED ``order`` visits every cell strictly before its downstream
      neighbour -- the exact topological order flow accumulation needs.

    Priority flood of Barnes et al. (2014). NaN cells are never visited. The heap
    key is ``(spill_elevation, i, j)`` with integer tie-breakers, so the whole
    construction is deterministic and host-independent.
    """
    z = _as_grid(z)
    rows, cols = z.shape
    filled = z.copy()
    flowdir = np.full((rows, cols), -1, dtype=np.int8)
    visited = np.zeros((rows, cols), dtype=bool)
    finite = np.isfinite(z)
    nodata = ~finite

    # Seeds (outlets): every border cell + every finite cell orthogonally
    # adjacent to a nodata cell. Marked visited; flow direction left at -1.
    border = np.zeros((rows, cols), dtype=bool)
    border[0, :] = border[-1, :] = border[:, 0] = border[:, -1] = True
    adj_nodata = np.zeros((rows, cols), dtype=bool)
    adj_nodata[1:, :] |= nodata[:-1, :]
    adj_nodata[:-1, :] |= nodata[1:, :]
    adj_nodata[:, 1:] |= nodata[:, :-1]
    adj_nodata[:, :-1] |= nodata[:, 1:]
    seed = finite & (border | adj_nodata)

    heap = []
    for idx in np.argwhere(seed):
        i, j = int(idx[0]), int(idx[1])
        visited[i, j] = True
        heapq.heappush(heap, (float(filled[i, j]), i, j))

    order = []
    while heap:
        e, i, j = heapq.heappop(heap)
        order.append((i, j))
        for d in range(8):
            di, dj = _NEIGHBORS[d]
            ni, nj = i + di, j + dj
            if 0 <= ni < rows and 0 <= nj < cols and finite[ni, nj] and not visited[ni, nj]:
                visited[ni, nj] = True
                zc = z[ni, nj]
                fv = zc if zc > e else e          # max(z, spill): the fill
                filled[ni, nj] = fv
                flowdir[ni, nj] = _OPPOSITE[d]    # drain back to (i, j)
                heapq.heappush(heap, (float(fv), ni, nj))
    return filled, flowdir, order


def fill_and_flowdirs(z):
    """Depression-filled surface and D8 flow directions (Barnes et al. 2014).

    Returns ``(filled, flowdir)``: ``filled`` is the float64 priority-flood
    surface (``>= z`` on finite cells, NaN preserved) and ``flowdir`` is the int8
    D8 direction grid (0..7 per :data:`_NEIGHBORS`, with ``-1`` at every outlet
    -- domain edge or nodata-adjacent cell -- and at every NaN cell). Every
    finite cell drains, acyclically, to some outlet with no flat ambiguity.
    """
    filled, flowdir, _ = _flood(z)
    return filled, flowdir


def fill_depressions(z):
    """Return just the depression-filled surface (priority flood).

    ``filled >= z`` on every finite cell (pits are raised to their spill level);
    NaN is preserved. Thin public wrapper over :func:`fill_and_flowdirs`.
    """
    return fill_and_flowdirs(z)[0]


def d8_flow_direction(z):
    """Return just the D8 flow-direction grid (int8).

    Direction index 0..7 (:data:`_NEIGHBORS`, clockwise from north) for every
    finite cell; ``-1`` at outlets (domain edge / nodata-adjacent) and NaN cells.
    Thin public wrapper over :func:`fill_and_flowdirs`.
    """
    return fill_and_flowdirs(z)[1]


def flow_accumulation(z):
    """Upstream-cell count draining through each cell (depression-filled D8).

    Returns a float64 array shaped like ``z``: each finite cell holds the number
    of cells (itself included, so always ``>= 1``) whose flow path passes through
    it; NaN cells carry ``nan``. Computed as a single reverse pass over the flood
    order, so every cell is finalised before its downstream neighbour and the
    accumulation is exact. By construction ``1 <= acc <= n_finite`` on finite
    cells and the accumulations of the OUTLET cells (flowdir ``-1``) sum to
    exactly ``n_finite`` -- every cell drains to some outlet.
    """
    z = _as_grid(z)
    _filled, flowdir, order = _flood(z)
    acc = np.where(np.isfinite(z), 1.0, np.nan)
    for i, j in reversed(order):
        d = int(flowdir[i, j])
        if d >= 0:
            di, dj = _NEIGHBORS[d]
            acc[i + di, j + dj] += acc[i, j]
    return acc


def drainage_signature(z, dx=1.0, channel_quantile=0.95):
    """Compact, JSON-serialisable surface-dissection texture signature.

    Builds the depression-filled D8 :func:`flow_accumulation` field and reduces
    it to four plain Python floats::

        {"channel_fraction":       float,   # fraction of finite cells whose
                                            #   accumulation is at or above the
                                            #   channel_quantile of accumulation
         "mean_log_acc":           float,   # mean of log10(acc) over finite cells
         "max_acc_fraction":       float,   # max(acc) / n_finite, in (0, 1]
         "drainage_density_proxy": float}   # channel_fraction / dx (channels per
                                            #   unit length -- a documented proxy)

    ``channel_fraction`` thresholds accumulation at its own ``channel_quantile``
    (default 0.95), so it is close to ``1 - channel_quantile`` by construction
    and is reported as a reference channel-texture level rather than a roughness
    discriminator; ``mean_log_acc`` (organised, long accumulation) and
    ``max_acc_fraction`` (peak flow concentration) are the fields that actually
    separate an organised surface from a dissected one. ``drainage_density_proxy``
    follows Horton (1945) drainage density in spirit (channel cells per unit
    length) and is explicitly a proxy, not a mapped channel length.

    Parameters
    ----------
    z : 2-D array of elevations in metres (NaN = nodata).
    dx : grid spacing in metres (> 0); scales ``drainage_density_proxy``.
    channel_quantile : accumulation quantile (in [0, 1]) defining the channel
        threshold.

    All values are plain floats (``nan`` only if the grid has no finite cell, or
    for ``drainage_density_proxy`` if ``dx <= 0``), so the signature is
    JSON-serialisable and deterministic. Carries the module's claim firewall: a
    purely geometric dissection-texture descriptor -- NOT a water, fluvial,
    climate, hazard, or mission claim on any body.
    """
    z = _as_grid(z)
    acc = flow_accumulation(z)
    vals = acc[np.isfinite(acc)]
    n = int(vals.size)
    nan = float("nan")
    if n == 0:
        return {"channel_fraction": nan, "mean_log_acc": nan,
                "max_acc_fraction": nan, "drainage_density_proxy": nan}
    q = float(np.clip(float(channel_quantile), 0.0, 1.0))
    thresh = float(np.quantile(vals, q))
    channel_fraction = float(np.count_nonzero(vals >= thresh) / n)
    mean_log_acc = float(np.mean(np.log10(vals)))
    max_acc_fraction = float(np.max(vals) / n)
    dx = float(dx)
    density = channel_fraction / dx if dx > 0.0 else nan
    return {
        "channel_fraction": channel_fraction,
        "mean_log_acc": mean_log_acc,
        "max_acc_fraction": max_acc_fraction,
        "drainage_density_proxy": float(density),
    }




