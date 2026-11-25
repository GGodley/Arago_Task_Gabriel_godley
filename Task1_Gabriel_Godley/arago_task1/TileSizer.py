#!/usr/bin/env python3
"""Tile Sizer: start here. One entry point for everything in this package.

    python TileSizer.py                                         open the interface in your browser
    python TileSizer.py --dims 2048 2048 2048 --hw 8 20 256     model the report's design on one workload
    python TileSizer.py --trace example/traces/mm_512x512x512.json --hw 8 20 256
    python TileSizer.py --dims 2048 2048 2048 --opt target      let the optimiser size the hardware
    python TileSizer.py --report                                regenerate every figure and table in the report
    python TileSizer.py --examples                              run every example trace (example/workloads.json)
    python TileSizer.py --test                                  run the test suite (needs pytest)

Single runs are saved in results/run_001, run_002, ...; the report figures in results/report/;
the examples in results/examples/ (see README.md).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description="Tile Sizer: analytical performance model and hardware optimiser")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dims", nargs=3, type=int, metavar=("M", "K", "N"), help="run once for these dimensions")
    g.add_argument("--trace", type=Path, help="run once for this trace file (.csv or .json)")
    g.add_argument("--report", action="store_true", help="regenerate the report's Figures 1-4 and tables")
    g.add_argument("--examples", action="store_true", help="run every example in example/workloads.json")
    g.add_argument("--test", action="store_true", help="run the test suite with pytest")
    ap.add_argument("--hw", nargs=3, type=int, metavar=("ND", "NM", "S"),
                    help="fixed hardware: DMA units, matrix units, local-memory tiles (report design: 8 20 256)")
    ap.add_argument("--opt", choices=["target", "speed", "hw"], default="target",
                    help="optimiser goal when --hw is not given (default: target, the report's rule)")
    ap.add_argument("--out", type=Path, help="output folder for --report (default results/report)")
    ap.add_argument("--no-browser", action="store_true", help="start the interface without opening a browser")
    a = ap.parse_args(argv)
    if a.report:
        cmd = [sys.executable, str(ROOT / "graphs" / "make_all.py")] + (["--out", str(a.out)] if a.out else [])
        raise SystemExit(subprocess.call(cmd))
    if a.examples:
        from tilesizer.cli import main as cli
        cli(["examples"])
        return
    if a.test:
        raise SystemExit(subprocess.call([sys.executable, "-m", "pytest", "-q", str(ROOT / "tests")], cwd=ROOT))
    if a.dims or a.trace:
        from tilesizer.run import run
        run(dims=a.dims, trace=a.trace, opt=a.opt, hw=a.hw)
    else:
        if a.hw:
            ap.error("--hw needs --dims or --trace")
        from tilesizer.gui import main as gui
        gui(open_browser=not a.no_browser)


if __name__ == "__main__":
    main()
