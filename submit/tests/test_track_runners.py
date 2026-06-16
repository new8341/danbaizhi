"""Tests for track runners (mini fixtures)."""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submit.tracks.baxiangfenzi import BaxiangfenziRunner
from submit.tracks.drugclip import DrugclipRunner
from submit.tracks.registry import get_runner
from submit.tracks.shenjingsuanzi import ShenjingsuanziRunner


def test_registry_unknown_track_fails() -> None:
    with pytest.raises(SystemExit):
        get_runner("not_a_track")


def test_drugclip_mini(tmp_path: Path) -> None:
    benchmark = ROOT / "submit" / "tests" / "fixtures" / "drugclip_mini"
    staging = tmp_path / "staging"
    runner = DrugclipRunner()
    import os

    os.environ["DRUGCLIP_BENCHMARK_ROOT"] = str(benchmark)
    os.environ["DRUGCLIP_MAX_TASKS"] = "1"
    try:
        runner.run(tmp_path / "saisdata", staging, tmp_path)
    finally:
        os.environ.pop("DRUGCLIP_BENCHMARK_ROOT", None)
        os.environ.pop("DRUGCLIP_MAX_TASKS", None)

    assert (staging / "result.csv").is_file()
    assert (staging / "result.log").is_file()
    text = (staging / "result.csv").read_text(encoding="utf-8")
    assert "mini_task__L000001" in text
    assert "mini_task__L000002" in text
    log_text = (staging / "result.log").read_text(encoding="utf-8")
    assert "hybrid_max_qed" in log_text
    assert "[agent] phase=done" in log_text


def test_baxiangfenzi_with_target_pdb(tmp_path: Path) -> None:
    pytest.importorskip("rdkit")
    saisdata = tmp_path / "saisdata"
    saisdata.mkdir()
    pdb = ROOT / "documen" / "Baxiangfenzi" / "target.pdb"
    if pdb.is_file():
        (saisdata / "target.pdb").write_text(pdb.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        (saisdata / "target.pdb").write_text("ATOM      1  CA  ALA A   1       0.000   0.000   0.000\n", encoding="utf-8")
    staging = tmp_path / "staging"
    import os

    os.environ["BAXIANG_MAX_CANDIDATES"] = "12"
    os.environ["BAXIANG_MAX_DOCK"] = "3"
    try:
        BaxiangfenziRunner().run(saisdata, staging, tmp_path)
    finally:
        os.environ.pop("BAXIANG_MAX_CANDIDATES", None)
        os.environ.pop("BAXIANG_MAX_DOCK", None)
    for i in (1, 2, 3):
        csv_path = staging / f"result{i}.csv"
        assert csv_path.is_file()
        text = csv_path.read_text(encoding="utf-8")
        assert "mol_smiles" in text
        assert ">>" in text
    assert (staging / "result.log").is_file()
    assert "[agent]" in (staging / "result.log").read_text(encoding="utf-8")


def test_shenjingsuanzi_ks_baseline_from_test(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    import numpy as np

    p1 = tmp_path / "saisdata" / "49" / "problem1"
    data_dir = p1 / "data"
    data_dir.mkdir(parents=True)
    with h5py.File(data_dir / "KS_test_A.hdf5", "w") as f:
        f.create_dataset("tensor", data=np.zeros((2, 20, 256), dtype=np.float16))
        f.create_dataset("t-coordinate", data=np.arange(20, dtype=np.float16) * 0.5)
        f.create_dataset("x-coordinate", data=np.arange(256, dtype=np.float16))

    p2 = tmp_path / "saisdata" / "49" / "problem2"
    sample_dir = p2 / "sample_submission"
    sample_dir.mkdir(parents=True)
    with h5py.File(sample_dir / "cylinder_pred_A.hdf5", "w") as f:
        f.create_dataset("tensor", data=np.zeros((1, 200, 64, 128, 2), dtype=np.float16))

    staging = tmp_path / "staging"
    ShenjingsuanziRunner().run(tmp_path / "saisdata", staging, tmp_path)
    assert (staging / "KS_pred_A.hdf5").is_file()
    with h5py.File(staging / "KS_pred_A.hdf5", "r") as f:
        assert f["tensor"].shape == (2, 400, 256)


def test_shenjingsuanzi_sample_fallback(tmp_path: Path) -> None:
    h5py = pytest.importorskip("h5py")
    import numpy as np

    saisdata = tmp_path / "saisdata" / "49"
    for problem, shape in (
        ("problem1", (1, 400, 256)),
        ("problem2", (1, 200, 64, 128, 2)),
    ):
        sample_dir = saisdata / problem / "sample_submission"
        sample_dir.mkdir(parents=True)
        name = "KS_pred_A.hdf5" if problem == "problem1" else "cylinder_pred_A.hdf5"
        with h5py.File(sample_dir / name, "w") as f:
            f.create_dataset("tensor", data=np.zeros(shape, dtype=np.float16))

    staging = tmp_path / "staging"
    ShenjingsuanziRunner().run(tmp_path / "saisdata", staging, tmp_path)
    assert (staging / "KS_pred_A.hdf5").is_file()
    assert (staging / "cylinder_pred_A.hdf5").is_file()
