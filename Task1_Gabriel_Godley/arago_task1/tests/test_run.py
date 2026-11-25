"""Numbered runs: folders count up, and a run writes the answer and the report graphs."""

from pathlib import Path

import pytest

from tilesizer.run import next_run_dir, run

ROOT = Path(__file__).resolve().parents[1]


def test_run_folders_count_up(tmp_path):
    assert next_run_dir(tmp_path).name == "run_001"
    assert next_run_dir(tmp_path).name == "run_002"
    (tmp_path / "run_009").mkdir()
    assert next_run_dir(tmp_path).name == "run_010"


def test_run_writes_answer(tmp_path):
    r = run(trace=ROOT / "example/traces/mm_256x256x256.csv", opt="hw", results=tmp_path, log=lambda *_: None)
    d = Path(r["folder"])
    assert d.name == "run_001"
    for f in ["summary.txt", "summary.json", "curves.csv", "timeline.png"]:
        assert (d / f).is_file(), f
    assert r["hardware"]["Nm"] == 1 and r["ticks"] > 0
    fast = run(dims=(256, 256, 256), opt="speed", results=tmp_path, log=lambda *_: None)
    assert fast["run"] == "run_002" and fast["ticks"] < r["ticks"] and fast["hardware"]["Nm"] > 1


def test_report_design_numbers(tmp_path):
    """The report's headline numbers on Nd = 8, Nm = 20, S = 256."""
    small = run(dims=(128, 128, 128), hw=(8, 20, 256), results=tmp_path, log=lambda *_: None)
    large = run(dims=(2048, 2048, 2048), hw=(8, 20, 256), results=tmp_path, log=lambda *_: None)
    assert small["ticks"] == 10 and small["limiter"] == "path"
    assert large["ticks"] == 3234 and large["matrix_util"] == pytest.approx(99.74, abs=0.01)
    assert large["mem_peak"] == pytest.approx(80.9, abs=0.05)
    target = run(dims=(2048, 2048, 2048), opt="target", results=tmp_path, log=lambda *_: None)
    assert (target["hardware"]["Nd"], target["hardware"]["Nm"], target["hardware"]["S"]) == (8, 20, 256)


def test_report_figures_regenerate(tmp_path):
    """graphs/make_all.py writes all four report figures and the tables."""
    import subprocess
    import sys
    subprocess.run([sys.executable, str(ROOT / "graphs" / "make_all.py"), "--out", str(tmp_path)], check=True,
                   capture_output=True)
    for f in ["fig1_methodology_flow.png", "fig2_bottleneck_transition.png", "fig3_memory_vs_dma.png",
              "fig4_memory_over_time.png", "report_tables.md"]:
        assert (tmp_path / f).is_file(), f
    assert "MISMATCH" not in (tmp_path / "report_tables.md").read_text(encoding="utf-8")
