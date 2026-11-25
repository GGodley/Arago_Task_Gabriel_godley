#!/usr/bin/env python3
"""Regenerate every figure and table in the report (Figures 1-4 and report_tables.md).

    python graphs/make_all.py [--out DIR]          default DIR: results/report/
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = ["fig1_methodology.py", "fig2_bottleneck.py", "fig3_memory_vs_dma.py",
           "fig4_memory_over_time.py", "report_tables.py"]


def main(argv=None) -> None:
    argv = list(sys.argv[1:] if argv is None else argv)
    for s in SCRIPTS:
        print(f"== {s}", flush=True)
        subprocess.run([sys.executable, str(HERE / s), *argv], check=True,
                       stdout=subprocess.DEVNULL if s == "report_tables.py" else None)
    print("done")


if __name__ == "__main__":
    main()
