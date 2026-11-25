"""Command line: python -m tilesizer <command> ...   (run with no command for a guided menu)

    translate  M K N            write the trace (list of tile operations) for a matmul
    model      input + hardware predict cycles, matrix usage and memory over time
    optimize   input + goal     find the cheapest Nd, Nm, S for a speed and size goal, then predict
    ladder     input            every speed step x memory step the optimizer can offer
    examples                    run every example in example/ and write results/
    dashboard                   open the interactive sizing page in the browser

An input is either --dims M K N or --trace FILE (.csv or .json, as written by `translate`).
"""

from __future__ import annotations

import argparse
import csv
import functools
import http.server
import json
import math
import threading
import webbrowser
from pathlib import Path

from . import api, report
from .optimizer import SIZES, SPEEDS, memory_ladder, plan, s_min, speed_for, speed_steps
from .counts import op_counts
from .parallelism import tilings
from .timing import LD, LM
from .translator import MatmulSpec, translate
from .workload import WorkloadError, category, from_dims, load_hardware, load_workload

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"


# ---- helpers --------------------------------------------------------------------

def _workload(a):
    if a.trace:
        return load_workload(a.trace)
    M, K, N = a.dims
    return from_dims(M, K, N)


def _add_input(p):
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--dims", nargs=3, type=int, metavar=("M", "K", "N"), help="C (MxN) = A (MxK) @ B (KxN)")
    g.add_argument("--trace", type=Path, help="trace file (.csv or .json)")


def _finish(r, out, plot):
    print(report.summary_text(r))
    path = report.write(r, out, plot=plot)
    print(f"\nwrote {path}/summary.json, curves.csv" + (", timeline.png" if plot else ""))


# ---- commands -------------------------------------------------------------------

def cmd_translate(a):
    spec = MatmulSpec(a.M, a.K, a.N)
    tr = translate(spec)
    out = a.out or Path(f"{spec.label}.csv")
    out.parent.mkdir(parents=True, exist_ok=True)
    (tr.to_json if out.suffix.lower() == ".json" else tr.to_csv)(out)
    c = tr.hw_op_counts()
    print(f"{spec.label}: {len(tr.ops)} trace records, hardware ops {c}")
    print("wrote", out)


def cmd_model(a):
    wl = _workload(a)
    if a.hw:
        nd, nm, S = load_hardware(a.hw)
    elif None in (a.nd, a.nm, a.mem):
        raise SystemExit("model: give --hw FILE, or all of --nd, --nm and --mem")
    else:
        nd, nm, S = a.nd, a.nm, a.mem
    r = api.run_model(wl, nd, nm, S)
    _finish(r, a.out or RESULTS / "runs" / f"{wl.name}_Nd{nd}_Nm{nm}_S{S}", not a.no_plot)


def cmd_optimize(a):
    wl = _workload(a)
    r = api.run_optimizer(wl, a.speed, a.size)
    _finish(r, a.out or RESULTS / "runs" / f"{wl.name}_{a.speed}_{a.size}", not a.no_plot)


def ladder_rows(wl):
    """(P, target ticks, s_min, [(S, plan or None)]) for every speed step."""
    M, K, N = wl.M, wl.K, wl.N
    c = op_counts(M, K, N)
    W = c.COMPUTE + c.ACC
    ts = tilings(M, K, N)
    mems = memory_ladder(M, K, N, ts)
    rows = []
    for P in speed_steps(M, K, N):
        T = 2 * LD + math.ceil(W / P) * LM
        rows.append((P, T, s_min(M, K, N, T, ts), [(S, plan(M, K, N, T, S, ts)) for S in mems]))
    return mems, rows


def cmd_ladder(a):
    wl = _workload(a)
    mems, rows = ladder_rows(wl)
    print(f"{wl.name} ({wl.category}): each cell is Nd/Nm, '-' = memory too small for that speed\n")
    w = 9
    print("speed".ljust(8) + "target cycles".rjust(15) + "".join(f"S={s}".rjust(w) for s in mems))
    for P, T, _lo, cells in reversed(rows):
        print(f"{P}x".ljust(8) + f"{T * 128:,}".rjust(15) +
              "".join((f"{p['Nd']}/{p['Nm']}" if p else "-").rjust(w) for _S, p in cells))
    print("\nspeed presets: " + ", ".join(f"{s} = {speed_for(wl.M, wl.K, wl.N, s)}x" for s in SPEEDS))


def cmd_examples(a):
    ex = json.loads((ROOT / "example" / "workloads.json").read_text())
    out = RESULTS / "examples"
    rows = []
    for e in ex["model_runs"]:
        wl = load_workload(ROOT / e["trace"]) if "trace" in e else from_dims(*e["dims"], name=e["name"])
        hw = load_hardware(ROOT / e["hw"]) if "hw" in e else tuple(e["hardware"])
        r = api.run_model(wl, *hw)
        report.write(r, out / "model" / e["name"])
        rows.append(("model", e["name"], r))
    for e in ex["optimizer_runs"]:
        wl = from_dims(*e["dims"], name=e["name"])
        for speed in e.get("speeds", SPEEDS):
            for size in e.get("sizes", SIZES):
                r = api.run_optimizer(wl, speed, size)
                report.write(r, out / "optimizer" / f"{e['name']}_{speed}_{size}", plot=not a.fast)
                rows.append(("optimizer", f"{e['name']} {speed} {size}", r))
    hdr = ["mode", "run", "M", "K", "N", "category", "Nd", "Nm", "S", "cycles", "matrix_util_pct", "dma_util_pct",
           "mem_peak_pct", "mem_mean_pct", "limiter", "tiling"]
    with open(out / "summary.csv", "w", newline="") as f:
        wr = csv.writer(f)
        wr.writerow(hdr)
        for mode, name, r in rows:
            w, h = r["workload"], r["hardware"]
            wr.writerow([mode, name, w["M"], w["K"], w["N"], w["category"], h["Nd"], h["Nm"], h["S"], r["cycles"],
                         r["matrix_util"], r["dma_util"], r["mem_peak"], r["mem_mean"], r["limiter"], r["tiling"]])
    for mode, name, r in rows:
        h = r["hardware"]
        print(f"{mode:9} {name:42} Nd={h['Nd']:<3} Nm={h['Nm']:<4} S={h['S']:<6} {r['cycles']:>12,} cycles  "
              f"matrix {r['matrix_util']:5.1f}%  mem peak {r['mem_peak']:5.1f}%")
    print(f"\nwrote {len(rows)} runs to {out}/ and {out}/summary.csv")


def cmd_dashboard(a):
    app = ROOT / "app"
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(app))
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", a.port), handler)
    url = f"http://127.0.0.1:{srv.server_address[1]}/index.html"
    print(f"Dashboard at {url}  (Ctrl+C to stop)")
    if not a.no_browser:
        threading.Timer(0.5, webbrowser.open, (url,)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass


# ---- guided menu ------------------------------------------------------------------

def _pick(question, options):
    print(f"\n{question}")
    for i, (label, _v) in enumerate(options, 1):
        print(f"  {i}) {label}")
    while True:
        s = input("> ").strip()
        if s.isdigit() and 1 <= int(s) <= len(options):
            return options[int(s) - 1][1]
        print(f"  type a number from 1 to {len(options)}")


def _int(question, lo=1, hi=16384):
    while True:
        s = input(f"{question}: ").strip()
        if s.isdigit() and lo <= int(s) <= hi:
            return int(s)
        print(f"  a whole number from {lo} to {hi}")


def menu():
    print("tilesizer: performance model and hardware optimizer for tiled matmul")
    src = _pick("What do you want to size?", [
        ("A matrix multiplication I give by its dimensions", "dims"),
        ("A trace file (.csv or .json)", "trace"),
        ("One of the examples", "example"),
    ])
    if src == "dims":
        print("C (M x N) = A (M x K) @ B (K x N)")
        wl = from_dims(_int("M"), _int("K"), _int("N"))
    elif src == "trace":
        while True:
            p = Path(input("trace file path: ").strip()).expanduser()
            try:
                wl = load_workload(p)
                break
            except (OSError, WorkloadError, ValueError) as e:
                print(f"  {e}")
    else:
        wl = _pick("Which example?", [(f"{n} ({category(*d)})", from_dims(*d, name=n)) for n, d in [
            ("small_128", (128, 128, 128)), ("medium_512", (512, 512, 512)), ("large_2048", (2048, 2048, 2048)),
            ("llm_decode_64x4096x4096", (64, 4096, 4096))]])
    print(f"\n{wl.name}: {wl.M} x {wl.K} x {wl.N} -> {category(wl.M, wl.K, wl.N)} matmul")
    goal = _pick("What is the goal?", [
        ("Find the cheapest hardware for a speed and size goal (optimizer)", "optimize"),
        ("I have the hardware: predict cycles, usage and memory (model)", "model"),
    ])
    if goal == "optimize":
        sp = speed_steps(wl.M, wl.K, wl.N)
        speed = _pick("Speed goal?", [(f"{s} ({speed_for(wl.M, wl.K, wl.N, s)}x of {sp[-1]}x max)", s) for s in SPEEDS])
        size = _pick("Size goal?", [("tiny: the least memory that meets the speed", "tiny"),
                                    ("compact: balanced memory, fewer DMA units", "compact")])
        r = api.run_optimizer(wl, speed, size)
        out = RESULTS / "runs" / f"{wl.name}_{speed}_{size}"
    else:
        nd = _pick("DMA units Nd?", [(str(v), v) for v in (1, 2, 4, 8, 16, 32, 64)])
        nm = _pick("Matrix units Nm?", [(str(v), v) for v in (1, 2, 4, 8, 16, 32, 64, 128)])
        S = _pick("Local memory S (tiles)?", [(str(v), v) for v in (4, 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096)])
        try:
            r = api.run_model(wl, nd, nm, S)
        except api.InfeasibleError as e:
            raise SystemExit(str(e))
        out = RESULTS / "runs" / f"{wl.name}_Nd{nd}_Nm{nm}_S{S}"
    print()
    _finish(r, out, True)


# ---- entry point --------------------------------------------------------------------

def main(argv=None):
    ap = argparse.ArgumentParser(prog="python -m tilesizer", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("translate", help="matrix dimensions -> trace file")
    p.add_argument("M", type=int), p.add_argument("K", type=int), p.add_argument("N", type=int)
    p.add_argument("--out", type=Path, help="output .csv or .json (default mm_MxKxN.csv)")
    p.set_defaults(fn=cmd_translate)

    p = sub.add_parser("model", help="workload + hardware -> cycles, usage, memory over time")
    _add_input(p)
    p.add_argument("--hw", type=Path, help="hardware JSON (see example/hw_*.json)")
    p.add_argument("--nd", type=int, help="DMA units")
    p.add_argument("--nm", type=int, help="matrix units")
    p.add_argument("--mem", type=int, help="local memory S, in 64x64 tiles")
    p.add_argument("--out", type=Path), p.add_argument("--no-plot", action="store_true")
    p.set_defaults(fn=cmd_model)

    p = sub.add_parser("optimize", help="workload + goal -> cheapest hardware and its outputs")
    _add_input(p)
    p.add_argument("--speed", choices=SPEEDS, default="fast")
    p.add_argument("--size", choices=SIZES, default="compact")
    p.add_argument("--out", type=Path), p.add_argument("--no-plot", action="store_true")
    p.set_defaults(fn=cmd_optimize)

    p = sub.add_parser("ladder", help="the full speed x memory table for a workload")
    _add_input(p)
    p.set_defaults(fn=cmd_ladder)

    p = sub.add_parser("examples", help="run example/workloads.json, write results/examples/")
    p.add_argument("--fast", action="store_true", help="skip the optimizer runs' plots")
    p.set_defaults(fn=cmd_examples)

    p = sub.add_parser("dashboard", help="serve app/ and open it in the browser")
    p.add_argument("--port", type=int, default=8000), p.add_argument("--no-browser", action="store_true")
    p.set_defaults(fn=cmd_dashboard)

    a = ap.parse_args(argv)
    if not a.cmd:
        try:
            return menu()
        except (KeyboardInterrupt, EOFError):
            print()
            return 1
    try:
        a.fn(a)
    except (WorkloadError, api.InfeasibleError, ValueError) as e:
        raise SystemExit(f"error: {e}")
    return 0
