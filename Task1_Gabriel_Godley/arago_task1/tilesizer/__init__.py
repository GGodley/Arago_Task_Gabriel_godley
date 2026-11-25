"""tilesizer: a closed-form performance model and hardware optimizer for blocked
matrix multiplication on a tile engine (DMA units + matrix units + local memory).

Pipeline (each step is a separate function, so they can be used alone or together):

    translator.translate(MatmulSpec(M, K, N))  -> Trace        matrix -> list of tile operations
    workload.shape_from_trace(trace)           -> Workload     trace -> the shape (M, K, N) the model needs
    workload.from_dims(M, K, N)                -> Workload     or skip the trace and give the shape
    api.run_model(workload, Nd, Nm, S)         -> result       hardware given: cycles, usage, memory
    api.run_optimizer(workload, speed, size)   -> result       goal given: cheapest Nd, Nm, S + the same outputs
    report.write(result, folder)                               summary.json, curves.csv, timeline.png

The modules counts, parallelism, timing, profile and optimizer hold the equations;
see docs/equations.md.
"""

from .counts import TILE, OpCounts, cdiv, loads_with_memory, op_counts, overlap_overhead, tiles
from .parallelism import Tiling, in_flight_work, little_memory, tilings
from .timing import LD, LM, Timing, predict_time

__version__ = "1.0.0"

__all__ = ["TILE", "OpCounts", "cdiv", "loads_with_memory", "op_counts", "overlap_overhead", "tiles", "LD", "LM",
           "Timing", "predict_time", "Tiling", "tilings", "in_flight_work", "little_memory"]
