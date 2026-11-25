"""The dashboard computes in the browser with app/model.js. It must agree with the Python."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tilesizer.optimizer import grid  # noqa: E402

NODE = shutil.which("node")
DIMS = [(64, 64, 64), (128, 128, 128), (512, 512, 512), (64, 4096, 4096), (100, 200, 300), (4096, 64, 4096)]
KEYS = ["Nd", "Nm", "tiling", "T", "T_plan", "limiter", "util", "dma_util", "mem_needed_pct", "mem_peak", "mem_mean"]


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
@pytest.mark.parametrize("dims", DIMS)
def test_js_grid_matches_python(dims):
    js = ("const M=require(process.argv[1]);const g=M.grid(...JSON.parse(process.argv[2]));"
          "for(const r of g.cells)for(const c of r)if(c){delete c.t;delete c.mat;delete c.dma;delete c.mem}"
          "process.stdout.write(JSON.stringify(g))")
    out = subprocess.run([NODE, "-e", js, str(ROOT / "app" / "model.js"), json.dumps(list(dims))],
                         capture_output=True, text=True, check=True).stdout
    j, p = json.loads(out), grid(*dims)
    for key in ("speeds", "targets", "mems", "s_min", "s_sat"):
        assert j[key] == p[key], key
    for rj, rp in zip(j["cells"], p["cells"]):
        for cj, cp in zip(rj, rp):
            assert (cj is None) == (cp is None)
            if cp:
                for k in KEYS:
                    assert cj[k] == pytest.approx(cp[k], abs=0.11), k


@pytest.mark.skipif(NODE is None, reason="Node.js not installed")
def test_js_reads_traces_like_python():
    from tilesizer.workload import load_workload
    for f in sorted((ROOT / "example" / "traces").iterdir()):
        js = ("const M=require(process.argv[1]);const fs=require('fs');"
              "process.stdout.write(JSON.stringify(M.shapeFromTrace(fs.readFileSync(process.argv[2],'utf8'),process.argv[2])))")
        w = json.loads(subprocess.run([NODE, "-e", js, str(ROOT / "app" / "model.js"), str(f)],
                                      capture_output=True, text=True, check=True).stdout)
        p = load_workload(f)
        assert (w["K"], sorted((w["M"], w["N"]))) == (p.K, sorted((p.M, p.N)))
