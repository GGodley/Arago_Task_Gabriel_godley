"""Shared helpers for the report figure scripts: repo import path, output folder, colours."""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tilesizer.counts import cdiv, tiles  # noqa: E402
from tilesizer.timing import LD, LM, _tilings, predict_time  # noqa: E402

DEFAULT_OUT = ROOT / "results" / "report"
INK, SUB, GRID = "#191919", "#666666", "#e6e6e6"
BLUE, ORANGE, AQUA = "#257de0", "#f47230", "#00b894"

# The report's recommended design (Section 1.3): Nd DMA units, Nm matrix units, S tiles.
ND, NM, S = 8, 20, 256


def out_dir(argv=None, desc: str = "") -> Path:
    ap = argparse.ArgumentParser(description=desc)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help=f"output folder (default {DEFAULT_OUT})")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    return a.out


def style(ax):
    ax.grid(True, which="major", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color("#bdbdbd")
    ax.tick_params(colors=SUB, labelsize=8.5)


def bounds(M, K, N, nd, nm, s):
    """The three lower bounds of the analytical model (ticks) and the predicted time T."""
    m, k, n = tiles(M, K, N)
    acc = 1 if k > 1 else 0
    W, Sv = m * n * (2 * k - 1), m * n
    tmat = 2 * LD + LM * (1 + cdiv(W - min(nm, Sv), nm))
    tpath = LD * cdiv(2, min(nd, 2)) + LM * (1 + (math.ceil(math.log2(k)) if k > 1 else 0)) + LD
    tau = LD + LM * (1 + acc)
    tdma = min((L + Sv) * max(LD / nd, tau / (s - R - 1)) for _, L, R in _tilings(m, k, n) if s - R - 1 >= 2)
    tdma0 = (k * (m + n) + Sv) * LD / nd  # perfect reuse: every A and B tile loaded once
    p = predict_time(M, K, N, nd, nm, s)
    return dict(tmat=tmat, tpath=tpath, tdma=tdma, tdma0=tdma0, T=p.T, lim=p.limiter, W=W)
