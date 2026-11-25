"""The two entry points: the model (hardware given) and the optimizer (goal given).

Both return the same result dictionary, so the outputs, report and graphs are shared:

    workload    M, K, N, tiles, category, where the shape came from
    hardware    Nd, Nm, S
    cycles      total cycles (ticks x 128)
    ticks       total time in ticks (1 tick = 128 cycles = one matrix op)
    matrix_util average matrix unit usage over the run, %
    dma_util    average DMA unit usage over the run, %
    mem_peak    peak local memory needed, % of S   (mem_mean: average)
    limiter     what sets the time: matrix, dma or path (dependency chain)
    tiling      the tiling the model assumes the scheduler uses
    curves      t (ticks), matrix_pct, dma_pct, mem_pct (needed), mem_prefetch_pct
"""

from __future__ import annotations

from .counts import op_counts
from .optimizer import choose
from .profile import profile
from .timing import LD
from .workload import Workload

TICK_CYCLES = 128


class InfeasibleError(ValueError):
    pass


def run_model(wl: Workload, nd: int, nm: int, S: int, points: int = 400) -> dict:
    """Predict cycles, usage and memory over time for a workload on given hardware."""
    if min(nd, nm, S) < 1:
        raise InfeasibleError("Nd, Nm and S must all be at least 1")
    p = profile(wl.M, wl.K, wl.N, nd, nm, S, points=points)
    if p is None:
        k = wl.tiles[1]
        raise InfeasibleError(f"S = {S} tiles is too small to run {wl.M}x{wl.K}x{wl.N}: "
                              f"it needs at least {4 if k > 1 else 3} tiles")
    return _result(wl, nd, nm, S, p, mode="model")


def run_optimizer(wl: Workload, speed: str, size: str, points: int = 400) -> dict:
    """Cheapest hardware for a speed goal and a size goal, then the model's outputs on it."""
    ch = choose(wl.M, wl.K, wl.N, speed, size)
    p = profile(wl.M, wl.K, wl.N, ch["Nd"], ch["Nm"], ch["S"], points=points)
    r = _result(wl, ch["Nd"], ch["Nm"], ch["S"], p, mode="optimizer")
    r["goal"] = {"speed": speed, "size": size, "speed_step_P": ch["P"], "target_ticks": ch["target"],
                 "target_cycles": ch["target"] * TICK_CYCLES, "planned_tiling": ch["tiling"],
                 "memory_needed_tiles": round(ch["mem_needed"], 1),
                 "least_memory_for_speed": round(ch["s_min"], 1),
                 "memory_where_more_stops_helping": round(ch["s_sat"], 1)}
    return r


def _result(wl: Workload, nd: int, nm: int, S: int, p: dict, mode: str) -> dict:
    c = op_counts(wl.M, wl.K, wl.N)
    m, k, n = wl.tiles
    return {
        "mode": mode,
        "workload": {"name": wl.name, "M": wl.M, "K": wl.K, "N": wl.N, "tiles_m": m, "tiles_k": k, "tiles_n": n,
                     "category": wl.category, "shape_from": wl.source,
                     "COMPUTE": c.COMPUTE, "ACC": c.ACC, "SAVE": c.SAVE, "LOAD_min": c.LOAD},
        "hardware": {"Nd": nd, "Nm": nm, "S": S},
        "ticks": round(p["T"], 2),
        "cycles": round(p["T"] * TICK_CYCLES),
        "matrix_util": round(100 * p["util"], 2),
        "dma_util": round(100 * min(1.0, p["dma_util"]), 2),
        "mem_peak": round(p["mem_peak_pct"], 2),
        "mem_mean": round(p["mem_mean_pct"], 2),
        "mem_prefetch_peak": round(p["occ_peak_pct"], 2),
        "mem_prefetch_mean": round(p["occ_mean_pct"], 2),
        "limiter": p["limiter"],
        "tiling": p["tiling"],
        "phases": {"fill_ticks": round(p["t_fill"], 2), "drain_ticks": LD,
                   "steady_memory_tiles": round(p["base"], 2), "resident_tiles": p["resident"]},
        "curves": {"t": p["t"].tolist(), "matrix_pct": p["mat_pct"].tolist(), "dma_pct": p["dma_pct"].tolist(),
                   "mem_pct": p["mem_pct"].tolist(), "mem_prefetch_pct": p["occ_pct"].tolist()},
    }
