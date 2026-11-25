"""End to end: the command line writes the three outputs, and the optimizer meets its goal."""

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tilesizer import api  # noqa: E402
from tilesizer.cli import main  # noqa: E402
from tilesizer.optimizer import SIZES, SPEEDS, choose  # noqa: E402
from tilesizer.workload import from_dims  # noqa: E402


def test_model_command_writes_outputs(tmp_path):
    main(["model", "--trace", str(ROOT / "example/traces/mm_128x128x128.csv"),
          "--hw", str(ROOT / "example/hw_small_128.json"), "--out", str(tmp_path)])
    s = json.loads((tmp_path / "summary.json").read_text())
    assert s["cycles"] > 0 and 0 < s["matrix_util"] <= 100 and 0 < s["mem_peak"] <= 100
    assert (tmp_path / "curves.csv").exists() and (tmp_path / "timeline.png").exists()


def test_translate_command(tmp_path):
    out = tmp_path / "t.json"
    main(["translate", "100", "200", "300", "--out", str(out)])
    assert json.loads(out.read_text())["workload"]["M"] == 100


def test_infeasible_memory_is_an_error():
    with pytest.raises(SystemExit):
        main(["model", "--dims", "512", "512", "512", "--nd", "1", "--nm", "1", "--mem", "2", "--no-plot"])


@pytest.mark.parametrize("dims", [(128, 128, 128), (512, 512, 512), (64, 4096, 4096), (100, 200, 300)])
def test_optimizer_goals(dims):
    wl = from_dims(*dims)
    prev = None
    for speed in SPEEDS:
        tiny, compact = (choose(*dims, speed, s) for s in SIZES)
        assert tiny["S"] <= compact["S"] and compact["Nd"] <= tiny["Nd"]
        r = api.run_optimizer(wl, speed, "compact", points=60)
        assert r["ticks"] <= r["goal"]["target_ticks"] + 1e-6  # the model meets the target it was sized for
        if prev is not None:
            assert tiny["P"] >= prev  # faster goals never ask for less speed
        prev = tiny["P"]
