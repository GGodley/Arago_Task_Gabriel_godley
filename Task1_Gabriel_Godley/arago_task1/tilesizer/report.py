"""Write a result (from api.run_model or api.run_optimizer) to disk and to the terminal.

    <out>/summary.json   every number, no curves
    <out>/curves.csv     the three outputs over time, one row per sample
    <out>/timeline.png   matrix usage, DMA usage and local memory over time
"""

from __future__ import annotations

import csv
import json
from pathlib import Path

from matplotlib.ticker import FuncFormatter

from .plotting import AQUA, BLUE, GREYS, GRID, INK, INK2, ORANGE, SURFACE, plt

CYCLES = 128


def summary_text(r: dict) -> str:
    w, h = r["workload"], r["hardware"]
    lines = [
        f"Workload   {w['name']}: {w['M']} x {w['K']} x {w['N']}  ({w['tiles_m']} x {w['tiles_k']} x {w['tiles_n']} tiles, "
        f"{w['category']}; shape from {w['shape_from']})",
    ]
    if "goal" in r:
        g = r["goal"]
        lines.append(f"Goal       speed {g['speed']} ({g['speed_step_P']} matrix units' worth, target "
                     f"{g['target_cycles']:,} cycles), size {g['size']}")
    lines += [
        f"Hardware   Nd = {h['Nd']} DMA units, Nm = {h['Nm']} matrix units, S = {h['S']} tiles of local memory",
        "",
        f"Total cycles            {r['cycles']:,}  ({r['ticks']:,} ticks)",
        f"Matrix unit usage       {r['matrix_util']}% average",
        f"DMA unit usage          {r['dma_util']}% average",
        f"Local memory used       peak {r['mem_peak']}%, average {r['mem_mean']}%  "
        f"(with prefetch: peak {r['mem_prefetch_peak']}%, average {r['mem_prefetch_mean']}%)",
        f"Limited by              {r['limiter']}",
        f"Tiling assumed          {r['tiling']}",
    ]
    return "\n".join(lines)


def write(r: dict, out: str | Path, plot: bool = True) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    summary = {k: v for k, v in r.items() if k != "curves"}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    c = r["curves"]
    with open(out / "curves.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(["tick", "cycle", "matrix_busy_pct", "dma_busy_pct", "memory_needed_pct", "memory_prefetch_pct"])
        for row in zip(c["t"], c["matrix_pct"], c["dma_pct"], c["mem_pct"], c["mem_prefetch_pct"]):
            wr.writerow([round(row[0], 3), round(row[0] * CYCLES), *(round(x, 2) for x in row[1:])])
    if plot:
        timeline(r, out / "timeline.png")
    return out


def _style(ax, ylabel):
    ax.grid(True, axis="y", color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(INK2)
    ax.tick_params(colors=INK2, labelsize=9)
    ax.set_ylabel(ylabel, color=INK2, fontsize=10)
    ax.set_ylim(0, 108)


def timeline(r: dict, path: Path) -> None:
    w, h, c = r["workload"], r["hardware"], r["curves"]
    t = [x * CYCLES for x in c["t"]]
    fig, axes = plt.subplots(3, 1, figsize=(9, 8.2), dpi=150, sharex=True)
    fig.suptitle(f"{w['M']}x{w['K']}x{w['N']} on Nd={h['Nd']}, Nm={h['Nm']}, S={h['S']} tiles: "
                 f"{r['cycles']:,} cycles, {r['limiter']}-bound", x=0.06, ha="left", color=INK, fontsize=13)
    fig.text(0.06, 0.935, f"Tiling {r['tiling']}. Fill, steady state and drain, assuming a quasi-optimal schedule.",
             color=INK2, fontsize=10)
    panels = [
        (c["matrix_pct"], BLUE, f"matrix units busy, avg {r['matrix_util']:.0f}%", "matrix units busy (%)"),
        (c["dma_pct"], ORANGE, f"DMA units busy, avg {r['dma_util']:.0f}%", "DMA units busy (%)"),
        (c["mem_pct"], AQUA, f"memory needed, avg {r['mem_mean']:.0f}%", "local memory used (%)"),
    ]
    for ax, (y, col, lab, ylab) in zip(axes, panels):
        ax.fill_between(t, y, color=col, alpha=0.14, lw=0)
        ax.plot(t, y, color=col, lw=1.7, label=lab)
        _style(ax, ylab)
    axes[2].plot(t, c["mem_prefetch_pct"], color=GREYS[2], lw=1.3, ls=":",
                 label=f"with prefetch, avg {r['mem_prefetch_mean']:.0f}%")
    for ax in axes:
        ax.legend(loc="lower right", bbox_to_anchor=(1, 0.99), frameon=False, fontsize=9, ncol=2)
    axes[2].set_xlabel("time (cycles)", color=INK2, fontsize=10)
    axes[2].set_xlim(0, t[-1])
    axes[2].xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:,.0f}"))
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    fig.savefig(path, facecolor=SURFACE)
    plt.close(fig)
