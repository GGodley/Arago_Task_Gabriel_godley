"""From a trace (or plain dimensions) to the workload the model needs, and back.

The model only needs the matmul shape: every count it uses (COMPUTE, ACC, LOAD, SAVE)
is a closed-form function of m, k, n tiles (counts.py). A trace is reduced to that
shape in this order of preference:

    1. the trace's workload header has M, K and N                 (what translator.py writes)
    2. the tile names A_i_k / B_k_j / C_i_j or P_i_j_k give the tile grid
    3. the op counts alone: k = COMPUTE / SAVE, m + n = LOAD / k, m n = SAVE
       (the model is symmetric in m and n, so which root is m does not matter)

Then the trace's own op counts are checked against the closed form, so a trace that
is not a plain C = A @ B matmul is reported instead of silently mis-modelled.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from .counts import TILE, op_counts
from .trace import Trace, load_trace

_NAME = re.compile(r"^([ABCP])_(\d+)_(\d+)(?:_(\d+))?$")


class WorkloadError(ValueError):
    pass


@dataclass(frozen=True)
class Workload:
    M: int
    K: int
    N: int
    name: str
    source: str  # "dims", "trace header", "tile names" or "op counts"

    @property
    def tiles(self):
        return tuple(math.ceil(d / TILE) for d in (self.M, self.K, self.N))

    @property
    def category(self) -> str:
        return category(self.M, self.K, self.N)


def category(M: int, K: int, N: int) -> str:
    """small / medium / large by the largest dimension (same rule as the dashboard)."""
    d = max(M, K, N)
    return "small" if d <= 256 else "medium" if d <= 1024 else "large"


def from_dims(M: int, K: int, N: int, name: str | None = None) -> Workload:
    for d, v in (("M", M), ("K", K), ("N", N)):
        if not isinstance(v, int) or v < 1:
            raise WorkloadError(f"{d} must be a positive integer, got {v!r}")
    return Workload(M, K, N, name or f"mm_{M}x{K}x{N}", "dims")


def shape_from_trace(trace: Trace, default_name: str = "trace") -> Workload:
    """The matmul shape a trace describes (see module docstring), checked against its op counts."""
    w = trace.workload or {}
    name = str(w.get("name") or default_name)
    if all(isinstance(w.get(d), int) and w[d] > 0 for d in "MKN"):
        wl = Workload(w["M"], w["K"], w["N"], name, "trace header")
    else:
        wl = _from_names(trace, name) or _from_counts(trace, name)
    _check_counts(trace, wl)
    return wl


def load_workload(path: str | Path) -> Workload:
    """Read a trace file (.json or .csv, see trace.py) and return its matmul shape."""
    return shape_from_trace(load_trace(path), Path(path).stem)


def _from_names(trace: Trace, name: str) -> Workload | None:
    mx = {"i": 0, "k": 0, "j": 0}
    seen = False
    for op in trace.ops:
        for tile in (*op.srcs, op.dst):
            hit = _NAME.match(tile or "")
            if not hit:
                continue
            seen = True
            kind, a, b, c = hit.group(1), int(hit.group(2)), int(hit.group(3)), hit.group(4)
            idx = {"A": {"i": a, "k": b}, "B": {"k": a, "j": b}, "C": {"i": a, "j": b},
                   "P": {"i": a, "j": b, "k": int(c) if c else 0}}[kind]
            for key, v in idx.items():
                mx[key] = max(mx[key], v + 1)
    if not seen or not all(mx.values()):
        return None
    return Workload(mx["i"] * TILE, mx["k"] * TILE, mx["j"] * TILE, name, "tile names")


def _from_counts(trace: Trace, name: str) -> Workload:
    c = trace.hw_op_counts()
    comp, save, load = c["COMPUTE"], c["SAVE"], c["LOAD"]
    if not save or comp % save or not load:
        raise WorkloadError("cannot read a matmul shape from this trace: no M/K/N header, "
                            "no A_i_k / B_k_j tile names, and the op counts do not factor")
    k = comp // save
    s = load // k  # m + n
    disc = s * s - 4 * save
    r = math.isqrt(max(disc, 0))
    if load % k or disc < 0 or r * r != disc:
        raise WorkloadError(f"op counts {c} are not those of a C = A @ B matmul")
    m, n = (s + r) // 2, (s - r) // 2
    return Workload(m * TILE, k * TILE, n * TILE, name, "op counts")


def _check_counts(trace: Trace, wl: Workload) -> None:
    got = trace.hw_op_counts()
    c = op_counts(wl.M, wl.K, wl.N)
    want = {"LOAD": c.LOAD, "COMPUTE": c.COMPUTE, "ACC": c.ACC, "SAVE": c.SAVE}
    if got != want:
        raise WorkloadError(f"trace op counts {got} do not match a {wl.M}x{wl.K}x{wl.N} matmul, "
                            f"which needs {want}")


def load_hardware(path: str | Path) -> tuple[int, int, int]:
    """(Nd, Nm, S) from a JSON file. Accepts {"Nd", "Nm", "S"} or {"n_dma", "n_matrix", "local_mem_tiles"}."""
    d = json.loads(Path(path).read_text())
    try:
        nd = d.get("Nd", d.get("n_dma"))
        nm = d.get("Nm", d.get("n_matrix"))
        S = d.get("S", d.get("local_mem_tiles"))
        vals = int(nd), int(nm), int(S)
    except (TypeError, ValueError):
        raise WorkloadError(f"{path}: needs Nd, Nm and S (or n_dma, n_matrix, local_mem_tiles)") from None
    if min(vals) < 1:
        raise WorkloadError(f"{path}: Nd, Nm and S must be positive")
    return vals
