"""One numbered run: workload in, hardware chosen, report graphs and results out.

Each call makes the next folder results/run_001, run_002, ... and writes:

    summary.txt                 the answer in plain words: ticks, cycles, hardware used
    summary.json, curves.csv    every number, and the outputs over time
    timeline.png                matrix usage, DMA usage and local memory over time

The hardware is either given (hw = (Nd, Nm, S), e.g. the report's 8, 20, 256) or chosen
by the optimiser for one of three goals:

    target  the report's rule: fewest units that meet the "fast" timing target
            (preset "fast", "compact" memory). Gives 8/20/256 for 2048^3.
    speed   the fastest the work allows (preset "max"), in the "compact" memory
    hw      the least hardware: one matrix unit's worth of speed (preset "steady"),
            in the smallest memory that works ("tiny")

The report's figures and tables are not per-run: regenerate them with
`python TileSizer.py --report` (or graphs/make_all.py).
"""

from __future__ import annotations

import re
from pathlib import Path

from . import api, report
from .workload import Workload, from_dims, load_workload

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"

OPTIMISATIONS = {
    "target": ("fast", "compact", "Timing target: fewest units that meet the fast target (report rule)"),
    "speed": ("max", "compact", "Speed: fastest the work allows"),
    "hw": ("steady", "tiny", "Hardware: least hardware that runs it"),
}


def next_run_dir(results: Path = RESULTS) -> Path:
    """results/run_001, run_002, ...: one more than the highest number already there."""
    results.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in results.iterdir() if (m := re.fullmatch(r"run_(\d+)", p.name))]
    n = max(nums, default=0) + 1
    while True:  # another run may have taken the number in the meantime
        d = results / f"run_{n:03d}"
        try:
            d.mkdir()
            return d
        except FileExistsError:
            n += 1


def _workload(dims=None, trace=None) -> Workload:
    if trace:
        return load_workload(Path(trace))
    if not dims:
        raise ValueError("give the matrix dimensions or a trace file")
    M, K, N = (int(x) for x in dims)
    if min(M, K, N) < 1:
        raise ValueError("every dimension must be at least 1")
    return from_dims(M, K, N)


def plain_summary(r: dict, opt: str, run_dir: Path, trace=None) -> str:
    w, h, g = r["workload"], r["hardware"], r["goal"]
    lines = [
        f"Run        {run_dir.name}",
        f"Input      {'trace ' + Path(trace).name if trace else 'dimensions'}: "
        f"{w['M']} x {w['K']} x {w['N']} ({w['tiles_m']} x {w['tiles_k']} x {w['tiles_n']} tiles of 64 x 64)",
        (f"Goal       {OPTIMISATIONS[opt][2]} (speed preset {g['speed']}, memory preset {g['size']})" if opt in OPTIMISATIONS
         else "Goal       hardware given, model only"),
        "",
        f"Ticks taken       {r['ticks']:,.6g}  ({r['cycles']:,} cycles, 1 tick = 128 cycles)",
        f"Hardware used     {h['Nd']} DMA units, {h['Nm']} matrix units, {h['S']:,} tiles of local memory",
        f"Matrix usage      {r['matrix_util']}% average",
        f"DMA usage         {r['dma_util']}% average",
        f"Memory used       peak {r['mem_peak']}% of S, average {r['mem_mean']}%",
        f"Limited by        {r['limiter']}",
    ]
    return "\n".join(lines) + "\n"


def run(dims=None, trace=None, opt: str = "speed", results: Path = RESULTS, log=print, hw=None) -> dict:
    """Do one numbered run. Returns what the interface shows: ticks, hardware, files.

    hw = (Nd, Nm, S) runs the model on that hardware; otherwise the optimiser picks it for `opt`.
    """
    wl = _workload(dims, trace)
    if hw is not None:
        nd, nm, S = (int(x) for x in hw)
        opt = "given"
        d = next_run_dir(results)
        log(f"{d.name}: {wl.M} x {wl.K} x {wl.N} on Nd = {nd}, Nm = {nm}, S = {S}")
        r = api.run_model(wl, nd, nm, S)
        r.setdefault("goal", {"speed": None, "size": None})
    else:
        if opt not in OPTIMISATIONS:
            raise ValueError(f"optimisation must be one of {', '.join(OPTIMISATIONS)}")
        speed, size, _ = OPTIMISATIONS[opt]
        d = next_run_dir(results)
        log(f"{d.name}: {wl.M} x {wl.K} x {wl.N}, optimising for {opt}")
        r = api.run_optimizer(wl, speed, size)
    report.write(r, d)
    text = plain_summary(r, opt, d, trace)
    (d / "summary.txt").write_text(text)
    log(text)

    files = [d / "summary.txt", d / "summary.json", d / "curves.csv", d / "timeline.png"]
    log(f"done: everything is in {d}")
    return {"run": d.name, "folder": str(d), "ticks": r["ticks"], "cycles": r["cycles"],
            "hardware": r["hardware"], "matrix_util": r["matrix_util"], "dma_util": r["dma_util"],
            "mem_peak": r["mem_peak"], "limiter": r["limiter"], "workload": r["workload"],
            "goal": r["goal"], "summary": text,
            "files": [str(f.relative_to(d)).replace("\\", "/") for f in files]}
