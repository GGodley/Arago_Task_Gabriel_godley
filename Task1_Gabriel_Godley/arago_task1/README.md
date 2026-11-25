# Arago Task 1: Tile Sizer

An analytical performance model and hardware optimiser for a tiled matrix multiply
C = A·B running on an engine with **Nd DMA units**, **Nm matrix units** and **S tiles of local
memory**. This package contains everything behind the Task 1 report: the model, one launcher,
an example trace for every workload the report discusses, and the scripts that redraw every
figure and table in it.

All results come from the **analytical model only**. No simulator is used. The model assumes
a quasi-optimal schedule and counts the reloads that a memory of S tiles forces. Its times are
therefore lower-bound estimates.

**Recommended design (report Section 1.3):** Nd = 8 DMA units, Nm = 20 matrix units, S = 256 tiles.

---

## Quick start

1. **Verify the dependencies** (Python 3.10+, numpy, matplotlib)
   - **Mac:**
     ```
     python3 --version
     python3 -m pip install numpy matplotlib
     ```
   - **Windows:**
     ```
     python --version
     python -m pip install numpy matplotlib
     ```
2. **Navigate in the terminal to the `arago_task1` folder** (the one that contains `TileSizer.py`):
   ```
   cd path/to/arago_task1
   ```
3. **Run:**
   - **Mac:**
     ```
     python3 TileSizer.py
     ```
   - **Windows:**
     ```
     python TileSizer.py
     ```
   The interface opens in your browser. Keep the terminal open while you use it.Every single run writes:

- `summary.txt`: ticks, cycles, hardware, utilizations and the limiter, in plain words.
- `summary.json`: every number.
- `curves.csv`: matrix, DMA and memory usage over time.
- `timeline.png`: the same curves drawn.

Example:

```text
$ python TileSizer.py --dims 2048 2048 2048 --hw 8 20 256
Ticks taken       3,234  (413,952 cycles, 1 tick = 128 cycles)
Hardware used     8 DMA units, 20 matrix units, 256 tiles of local memory
Matrix usage      99.74% average
DMA usage         94.99% average
Memory used       peak 80.9% of S, average 80.4%
Limited by        matrix
```

The full command-line tool is also available as `python -m tilesizer <command>`:

| Command | Purpose |
|---|---|
| `translate` | Writes the trace for a matrix size |
| `model` | Runs the model on given hardware |
| `optimize` | Finds the cheapest hardware for a goal |
| `ladder` | Prints the full speed × memory table |
| `examples` | Runs every example |
| `dashboard` | Opens the browser dashboard |

Run `python -m tilesizer <command> --help` for the options of each command.

## 4. Figures and tables in the report

| Report item | Script | Output file in `results/report/` |
|---|---|---|
| Figure 1: method and model flow | `graphs/fig1_methodology.py` | `fig1_methodology_flow.png` |
| Figure 2, Experiment 1: bottleneck transition (fixed 8/20/256, N = 64 to 4096) | `graphs/fig2_bottleneck.py` | `fig2_bottleneck_transition.png`, `fig2_data.json` |
| Figure 3, Experiment 2: memory against DMA (2048³, matrix units at least 90% busy) | `graphs/fig3_memory_vs_dma.py` | `fig3_memory_vs_dma.png`, `fig3_data.json` |
| Figure 4, Experiment 4: local-memory occupancy over cycles on 8/20/256 (128³, 512³, 2048³) | `graphs/fig4_memory_over_time.py` | `fig4_memory_over_time.png`, `fig4_data.json` |
| Experiment 3 shape table, Table 1, validation table and every number in the bullets | `graphs/report_tables.py` | `report_tables.md` |
| All of the above | `graphs/make_all.py` (same as `python TileSizer.py --report`) | all of the above |

Each script also runs on its own, for example `python graphs/fig2_bottleneck.py --out somewhere/`.
The regenerated figures are pixel-identical to the ones in the report. The whole set takes
about 10 seconds.

## 5. Example traces

A trace lists every tile operation of one matmul (LOAD, COMPUTE, ACC, SAVE) and its
dependencies. It does not depend on the hardware. `example/workloads.json` runs each trace on
the hardware it was discussed with. The results go to `results/examples/<name>/`, with one line
per run in `results/examples/summary.csv`.

| Trace (`example/traces/`) | Where it appears in the report | Hardware | Model result |
|---|---|---|---|
| `mm_64x64x64.csv` | Fig 2, dependency-bound end | 8/20/256 | 9 ticks, critical-path limited |
| `mm_128x128x128.csv` | Small workload: Fig 4, Table 1, validation | 8/20/256 | 10 ticks (dependency floor), 6.0% matrix utilization |
| `mm_128x128x128.csv` | Table 1, minimum hardware for the small workload | `hw_small_128.json` (Nd 4, Nm 2, S 16) | 14 ticks, 42.9% matrix utilization |
| `mm_192x192x192.csv` | Fig 2, first DMA-limited size | 8/20/256 | DMA-limited |
| `mm_256x256x256.csv` | Experiment 3, square case | 8/20/256 | 16 output tiles, 48 minimum DMA transfers |
| `mm_512x512x512.json` | Fig 4, DMA-limited regime (also shows the JSON format) | 8/20/256 | 96 ticks, 50% matrix utilization, 33.9% memory peak |
| `mm_1024x1024x1024.csv` | Fig 2, last DMA-limited size | 8/20/256 | DMA-limited |
| `mm_2048x2048x2048.csv` | Large workload: Fig 3, Fig 4, Table 1 | 8/20/256 | 3,234 ticks, 99.7% matrix utilization, 80.9% memory peak |
| `mm_4096x4096x4096.csv` | Fig 2, compute-bound end | 8/20/256 | compute-limited (matrix 26,018 ticks against DMA 20,480 ticks) |
| `mm_64x4096x64.csv` | Experiment 3, long-K case | 8/20/256 | 1 output tile, 129 minimum DMA transfers |
| `mm_64x4096x4096.csv`, `mm_64x8192x64.csv` | Edge cases: skewed shapes | 8/20/256 | DMA-limited, 10-20% matrix utilization |
| `mm_100x200x300.csv` | Edge case: dimensions that are not multiples of 64 | 8/20/256 | padded to whole tiles |
| (dimensions only) 2048³ at S = 4 | Edge case: minimum memory | Nd 8, Nm 20, S 4 | 199,680 ticks |

Hardware files are in `example/`:

- `hw_recommended.json` (8/20/256), in the short format `{"Nd", "Nm", "S"}`.
- `hw_small_128.json` (4/2/16), in the long format (`n_dma`, `n_matrix`, `local_mem_tiles`, ...).

To make a trace for any other size:

```bash
python -m tilesizer translate M K N --out my_trace.csv
python TileSizer.py --trace my_trace.csv --hw 8 20 256
```

### Trace format

CSV starts with `# key=value` header lines (name, M, K, N, tile counts), then one operation per
row under the columns `id,type,srcs,dst,deps`. JSON stores the same header under `workload` and
the operations under `ops`.

| Type | Unit and time | srcs → dst |
|---|---|---|
| LOAD | DMA, 4 ticks | global memory → tile |
| COMPUTE | matrix unit, 1 tick | A, B → partial P |
| ACC | matrix unit, 1 tick per pair | partials P0 … Pk−1 → C (one reduction group, expanded into k−1 binary adds) |
| SAVE | DMA, 4 ticks | C → global memory |

The format is described in detail in `tilesizer/trace.py`.

## 6. How the model works (short)

All times are in ticks (1 tick = 128 cycles). Ld = 4 ticks per DMA transfer and Lm = 1 tick
per matrix operation. Tiles are 64×64, so m, k, n = ⌈M/64⌉, ⌈K/64⌉, ⌈N/64⌉.

```text
W      = m n (2k − 1)                         matrix work (COMPUTE + ACC)
Sv     = m n                                  saves
L(S)   = loads with S tiles, reloads included (block tiling bm×bn: k(m⌈n/bn⌉ + n⌈m/bm⌉))
T_mat  = 2Ld + ⌈W/Nm⌉ Lm                      matrix units busy
T_dma  = (L + Sv) · max(Ld/Nd, τ/F)           DMA busy, or memory slots run out (Little's law)
T_path = Ld⌈2/min(Nd,2)⌉ + Lm(1 + ⌈log2 k⌉) + Ld    dependency chain
T      = min over tilings of max(T_mat, T_dma, T_path)
U_m    = W·Lm / (Nm·T)                        average matrix-unit utilization
```

Here F = S − R − 1 is the number of slots free for tiles in flight, and τ = Ld + Lm(1 + acc).
The optimiser turns a speed goal P into a target T* = 2Ld + ⌈W/P⌉Lm, then finds the fewest
units that meet it. The "fast" preset gives P = 20 for 2048³ (T* = 3,234 ticks) and P = 2 for
128³ (T* = 14 ticks). The common design takes the larger need in each resource.

Variables and derivations are in `docs/equations.md`.

**Quasi-optimal schedule.** The model does not enumerate a schedule. It assumes:

- the best tiling for S;
- DMA transfers overlap computation;
- no unit idles while ready work exists;
- memory is never oversubscribed.

## 7. Validation and limitations

Validation, all model only (`python TileSizer.py --test`, plus `results/report/report_tables.md`):

- **Hand calculation:** 128³ on 8/20/256 is 4 + 2 + 4 = 10 ticks by hand, which matches the model.
- **Conservation:** the area under the matrix-usage curve equals the counted work W.
- **Optimiser:** every design it picks meets its target T*. The tests also check the trace
  counts against the closed form, the padding and edge cases, and the browser copy of the model.

Limitations:

- The quasi-optimal schedule means the times are lower bounds.
- Latencies are fixed, and bandwidth contention is not modelled.
- There is no workload distribution or hardware cost function, so 20/8/256 is a justified
  choice but not a uniquely optimal one.

## 8. Package layout

```text
TileSizer.py                 the launcher (start here)
requirements.txt             numpy, matplotlib
pyproject.toml               optional: pip install -e .  gives a `tilesizer` command
start_tilesizer.sh, Start TileSizer (Mac).command, Start TileSizer (Windows).bat
tilesizer/                   the model package
  counts.py                  Step 1: operation counts (W, Sv, L0)
  translator.py, trace.py    matmul → trace file; trace format, reading and validation
  workload.py                workload from dimensions or a trace; hardware files
  parallelism.py             tilings, reloads L(S), Little's-law memory
  timing.py                  the timing equations T_mat, T_dma, T_path → T
  profile.py                 usage and memory curves over time (fill, steady state, drain)
  optimizer.py               fewest (Nd, Nm, S) for a target; speed and memory presets
  api.py                     run_model (hardware given) and run_optimizer (goal given)
  run.py, report.py          numbered runs, summary files and timeline plot
  cli.py, __main__.py        `python -m tilesizer ...`
  gui.py, plotting.py        browser interface and plotting helpers
app/                         browser dashboard (same model in JavaScript)
graphs/                      scripts that redraw every figure and table in the report
example/                     traces/ (one per discussed workload), hardware files, workloads.json
docs/equations.md            the model's equations and variables
tests/                       58 tests
results/report/              report figures and tables (pre-generated, regenerated by --report)
results/examples/            example outputs (pre-generated, regenerated by --examples)
```
