#!/usr/bin/env python3
"""Recompute every number quoted in the report's tables and bullets, from the model only.

Writes report_tables.md next to the figures and prints it.

    python graphs/report_tables.py [--out DIR]
"""
from __future__ import annotations

import numpy as np

from _common import ND, NM, S, bounds, out_dir, predict_time, tiles, LM
from tilesizer import api
from tilesizer.profile import profile
from tilesizer.workload import from_dims

OUT = out_dir(desc="Report tables")
_trapz = getattr(np, "trapezoid", None) or np.trapz
lines: list[str] = []
say = lines.append


def util(r):
    return f"({r['matrix_util']:.1f}%, {r['dma_util']:.1f}%, {r['mem_peak']:.1f}%)"


# ---- Table 1: minimum hardware to reach the timing target ("fast" speed preset, compact memory) ----
say("## Table 1: minimum hardware to reach the timing target\n")
say("Optimizer goal: speed preset `fast`, memory preset `compact`. Common design = larger need in each resource.\n")
opt = {s: api.run_optimizer(from_dims(s, s, s), "fast", "compact") for s in (128, 2048)}
hw = {s: opt[s]["hardware"] for s in opt}
common = (max(hw[128]["Nd"], hw[2048]["Nd"]), max(hw[128]["Nm"], hw[2048]["Nm"]), max(hw[128]["S"], hw[2048]["S"]))
on_common = {s: api.run_model(from_dims(s, s, s), *common) for s in (128, 2048)}
say("| Parameter | Small (128³) | Large (2048³) | Common design |")
say("|---|---|---|---|")
say(f"| Matrix units | {hw[128]['Nm']} | {hw[2048]['Nm']} | {common[1]} |")
say(f"| DMA units | {hw[128]['Nd']} | {hw[2048]['Nd']} | {common[0]} |")
say(f"| Memory tiles | {hw[128]['S']} | {hw[2048]['S']} | {common[2]} |")
say(f"| Target T* (ticks) | {opt[128]['goal']['target_ticks'] if 'target_ticks' in opt[128]['goal'] else '-'} | "
    f"{opt[2048]['goal']['target_ticks'] if 'target_ticks' in opt[2048]['goal'] else '-'} | |")
say(f"| Execution time | {opt[128]['cycles']:,} cycles ({opt[128]['ticks']:,} ticks) | "
    f"{opt[2048]['cycles']:,} cycles ({opt[2048]['ticks']:,} ticks) | "
    f"small {on_common[128]['cycles']:,} cycles ({on_common[128]['ticks']:,} ticks); "
    f"large {on_common[2048]['cycles']:,} cycles ({on_common[2048]['ticks']:,} ticks) |")
say(f"| Utilization (matrix, DMA, memory peak) | {util(opt[128])} | {util(opt[2048])} | "
    f"small: {util(on_common[128])}; large: {util(on_common[2048])} |")
assert common == (ND, NM, S), f"common design {common} differs from the report's {ND}/{NM}/{S}"

# ---- Experiment 1 / Figure 2 facts ----
say(f"\n## Figure 2 facts (Nd = {ND}, Nm = {NM}, S = {S})\n")
dma_sizes = [n for n in range(64, 4097, 64) if (b := bounds(n, n, n, ND, NM, S))["lim"] == "dma"]
say(f"- DMA-limited square sizes: {dma_sizes[0]}³ to {max(n for n in dma_sizes if n <= 1024)}³ (and some larger sizes where reloads step up)")
b = bounds(4096, 4096, 4096, ND, NM, S)
say(f"- 4096³: matrix bound {b['tmat']:,.0f} ticks vs DMA bound {b['tdma']:,.0f} ticks -> limiter {b['lim']}")
for n in (64, 128, 1024, 4096):
    say(f"- dependency floor at {n}³: {bounds(n, n, n, ND, NM, S)['tpath']:.0f} ticks")

# ---- Experiment 2 / Figure 3 facts ----
say("\n## Figure 3 facts (2048³, matrix units >= 90% busy)\n")


def req_nd(M, nm, s, U=0.9, ndmax=128):
    m, k, n = tiles(M, M, M)
    tstar = m * n * (2 * k - 1) * LM / (nm * U)
    for nd in range(1, ndmax + 1):
        p = predict_time(M, M, M, nd, nm, s)
        if p and p.T <= tstar + 1e-9:
            return nd
    return None


for nm, s in [(32, 256), (32, 1024), (16, 256)]:
    say(f"- Nm = {nm}, S = {s}: fewest DMA units = {req_nd(2048, nm, s)}")

# ---- Experiment 3: workload shape ----
say("\n## Experiment 3: workload shape\n")
say("| Workload | Output tiles | COMPUTEs | ACCs | Minimum DMA transfers |")
say("|---|---:|---:|---:|---:|")
for name, d in [("Square 256", (256, 256, 256)), ("Rectangular 64x4096 (64x4096x64)", (64, 4096, 64))]:
    w = api.run_model(from_dims(*d), ND, NM, S)["workload"]
    say(f"| {name} | {w['SAVE']} | {w['COMPUTE']} | {w['ACC']} | {w['LOAD_min'] + w['SAVE']} |")

# ---- Experiment 4 / Figure 4 ----
say(f"\n## Figure 4: memory occupancy on {ND}/{NM}/{S}\n")
say("| Workload | Run | Avg matrix-unit util. | Avg DMA util. | Peak / mean occupancy | Tiling | Limiter |")
say("|---|---|---|---|---|---|---|")
for s in (128, 512, 2048):
    r = api.run_model(from_dims(s, s, s), ND, NM, S)
    say(f"| {s}³ | {r['cycles']:,} cycles ({r['ticks']:,} ticks) | {r['matrix_util']:.1f}% | {r['dma_util']:.1f}% | "
        f"{r['mem_peak']:.1f}% / {r['mem_mean']:.1f}% | {r['tiling']} | {r['limiter']} |")

# ---- 1.4 Validation (model only) ----
say("\n## Validation (model only)\n")
say("| Check | Result |")
say("|---|---|")
hand = 4 + (1 + 1) + 4  # LOAD A,B in parallel (Ld) + COMPUTE + one ACC level (k=2) + SAVE (Ld)
model = predict_time(128, 128, 128, ND, NM, S).T
say(f"| Hand calculation of 128³ on {NM}/{ND}/{S} | 4 + 2 + 4 = {hand} ticks; model gives {model:g} -> "
    f"{'match' if hand == model else 'MISMATCH'} |")
errs = []
for M, nd, nm, s in [(512, 8, 4, 128), (1024, 16, 16, 256), (2048, ND, NM, S)]:
    p = profile(M, M, M, nd, nm, s, points=20000)
    m = M // 64
    W = m * m * (2 * m - 1)
    errs.append(abs(_trapz(p["mat_pct"] / 100 * nm, p["t"]) / W - 1))
say(f"| Area under matrix-usage curve equals counted work W | max error {100 * max(errs):.2f}% over 3 workloads |")
ok = all(opt[s]["ticks"] <= (opt[s]["goal"].get("target_ticks") or float("inf")) for s in opt)
say(f"| Optimizer designs re-run through the timing model meet T* | {'yes' if ok else 'NO'} "
    f"(full check: `python -m pytest`) |")

text = "\n".join(lines) + "\n"
(OUT / "report_tables.md").write_text(text, encoding="utf-8")
print(text)
print("wrote", OUT / "report_tables.md")
