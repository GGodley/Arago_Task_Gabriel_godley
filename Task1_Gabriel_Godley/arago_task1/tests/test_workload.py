"""Translator -> trace -> shape: the round trip the model's input goes through."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tilesizer.trace import Op, Trace, load_trace  # noqa: E402
from tilesizer.translator import MatmulSpec, translate  # noqa: E402
from tilesizer.workload import WorkloadError, category, load_hardware, load_workload, shape_from_trace  # noqa: E402

DIMS = [(64, 64, 64), (128, 128, 128), (100, 200, 300), (64, 4096, 64), (512, 64, 256)]


def _tiles(M, K, N):
    return tuple(-(-d // 64) * 64 for d in (M, K, N))


@pytest.mark.parametrize("dims", DIMS)
def test_header_round_trip(dims, tmp_path):
    for ext in (".csv", ".json"):
        tr = translate(MatmulSpec(*dims))
        f = tmp_path / f"t{ext}"
        (tr.to_json if ext == ".json" else tr.to_csv)(f)
        wl = load_workload(f)
        assert (wl.M, wl.K, wl.N) == dims and wl.source == "trace header"


@pytest.mark.parametrize("dims", DIMS)
def test_tile_names_without_header(dims):
    tr = translate(MatmulSpec(*dims))
    wl = shape_from_trace(Trace(ops=tr.ops, workload={}))
    assert (wl.M, wl.K, wl.N) == _tiles(*dims) and wl.source == "tile names"


@pytest.mark.parametrize("dims", DIMS)
def test_op_counts_only(dims):
    tr = translate(MatmulSpec(*dims))
    names = {}
    rn = lambda t: t and names.setdefault(t, f"x{len(names)}")  # noqa: E731
    ops = [Op(o.id, o.type, tuple(rn(s) for s in o.srcs), rn(o.dst), o.deps) for o in tr.ops]
    wl = shape_from_trace(Trace(ops=ops, workload={}))
    m, k, n = (d // 64 for d in _tiles(*dims))
    assert wl.K == k * 64 and sorted((wl.M, wl.N)) == sorted((m * 64, n * 64)) and wl.source == "op counts"


def test_example_traces_load():
    for f in sorted((ROOT / "example" / "traces").iterdir()):
        load_workload(f)


def test_mismatched_header_is_rejected():
    tr = translate(MatmulSpec(128, 128, 128))
    with pytest.raises(WorkloadError):
        shape_from_trace(Trace(ops=tr.ops, workload={"M": 256, "K": 128, "N": 128}))


def test_trace_validation_catches_broken_deps(tmp_path):
    tr = translate(MatmulSpec(128, 128, 128))
    bad = [Op(o.id, o.type, o.srcs, o.dst, ()) if o.id == 2 else o for o in tr.ops]
    f = tmp_path / "bad.csv"
    Trace(ops=bad, workload=tr.workload).to_csv(f)
    with pytest.raises(ValueError):
        load_trace(f)


def test_hardware_files():
    assert load_hardware(ROOT / "example" / "hw_small_128.json") == (4, 2, 16)
    assert load_hardware(ROOT / "example" / "hw_recommended.json") == (8, 20, 256)


def test_category():
    assert [category(*d) for d in [(128,) * 3, (512,) * 3, (64, 4096, 4096)]] == ["small", "medium", "large"]
