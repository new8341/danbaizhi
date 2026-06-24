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
from submit.tracks.shenjingsuanzi_agent.pipeline import (
    CYLINDER_PRED_A,
    CYLINDER_PRED_B,
    KS_PRED_A,
    KS_PRED_B,
)


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
    assert "[agent] phase=done" in log_text
    assert "hybrid_max_qed_v2" in log_text or "neural" in log_text


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

    os.environ["BAXIANG_MAX_CANDIDATES"] = "80"
    os.environ["BAXIANG_MAX_DOCK"] = "40"
    os.environ["BAXIANG_SELECT_POOL"] = "20"
    try:
        BaxiangfenziRunner().run(saisdata, staging, tmp_path)
    finally:
        os.environ.pop("BAXIANG_MAX_CANDIDATES", None)
        os.environ.pop("BAXIANG_MAX_DOCK", None)
        os.environ.pop("BAXIANG_SELECT_POOL", None)
    for i in (1, 2, 3):
        csv_path = staging / f"result{i}.csv"
        assert csv_path.is_file()
        text = csv_path.read_text(encoding="utf-8")
        assert "mol_smiles" in text
        assert ">>" in text
    assert (staging / "result.log").is_file()
    assert "[agent]" in (staging / "result.log").read_text(encoding="utf-8")


def test_shenjingsuanzi_ks_baseline_from_test(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
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
    cyl_data = p2 / "data"
    cyl_data.mkdir(parents=True)
    with h5py.File(cyl_data / "cylinder_test_A.hdf5", "w") as f:
        f.create_dataset("tensor", data=np.zeros((1, 20, 64, 128, 2), dtype=np.float16))

    b_dir = tmp_path / "saisdata" / "66"
    b_dir.mkdir(parents=True)
    with h5py.File(b_dir / "KS_test_B.hdf5", "w") as f:
        f.create_dataset("tensor", data=np.zeros((2, 20, 256), dtype=np.float16))
        f.create_dataset("t-coordinate", data=np.arange(20, dtype=np.float16) * 0.5)
        f.create_dataset("x-coordinate", data=np.arange(256, dtype=np.float16))
    with h5py.File(b_dir / "cylinder_test_B.hdf5", "w") as f:
        f.create_dataset("tensor", data=np.zeros((1, 20, 64, 128, 2), dtype=np.float16))

    staging = tmp_path / "staging"

    def _mock_cylinder(problem_root, out_path, test_path=None):
        with h5py.File(out_path, "w") as f:
            f.create_dataset("tensor", data=np.zeros((1, 200, 64, 128, 2), dtype=np.float16))
        return "inference", ["[agent] cylinder_mock=inference"]

    import submit.tracks.shenjingsuanzi_agent.pipeline as sj_pipe

    monkeypatch.setattr(sj_pipe, "run_cylinder", _mock_cylinder)
    ShenjingsuanziRunner().run(tmp_path / "saisdata", staging, tmp_path)
    for name in (KS_PRED_A, KS_PRED_B, CYLINDER_PRED_A, CYLINDER_PRED_B):
        assert (staging / name).is_file(), name
    with h5py.File(staging / KS_PRED_A, "r") as f:
        assert f["tensor"].shape == (2, 400, 256)
    log_text = (tmp_path / "shenjingsuanzi_run.log").read_text(encoding="utf-8")
    assert "[agent] phase=done" in log_text


def test_drugclip_hybrid_v2_config() -> None:
    from submit.tracks.drugclip_agent.scoring import DEFAULT_CONFIG

    assert DEFAULT_CONFIG.qed_bonus == 0.04
    assert DEFAULT_CONFIG.smiles_sim_weight == 0.08


def test_shenjingsuanzi_ks_q1_preset() -> None:
    import os

    os.environ["SHENJING_KS_PRESET"] = "ks-q1"
    os.environ["SHENJING_KS_EPOCHS"] = "28"
    try:
        from submit.tracks.shenjingsuanzi_agent.config import load_ks_config

        cfg = load_ks_config()
        assert cfg.epochs == 28
        assert cfg.rollout_weight == 0.44
        assert len(cfg.pinned_window_starts) >= 5
    finally:
        os.environ.pop("SHENJING_KS_PRESET", None)
        os.environ.pop("SHENJING_KS_EPOCHS", None)


def test_shenjingsuanzi_rejects_sample_only_saisdata(tmp_path: Path) -> None:
    """Semifinal: no pre-copy from sample_submission; real test paths required."""
    h5py = pytest.importorskip("h5py")
    import numpy as np

    saisdata = tmp_path / "saisdata" / "49"
    for problem, names, shape in (
        ("problem1", (KS_PRED_A, KS_PRED_B), (1, 400, 256)),
        ("problem2", (CYLINDER_PRED_A, CYLINDER_PRED_B), (1, 200, 64, 128, 2)),
    ):
        sample_dir = saisdata / problem / "sample_submission"
        sample_dir.mkdir(parents=True)
        for name in names:
            with h5py.File(sample_dir / name, "w") as f:
                f.create_dataset("tensor", data=np.zeros(shape, dtype=np.float16))

    staging = tmp_path / "staging"
    with pytest.raises(SystemExit):
        ShenjingsuanziRunner().run(tmp_path / "saisdata", staging, tmp_path)


def test_baxiangfenzi_official_composite_rematch_weights() -> None:
    from submit.tracks.baxiangfenzi_agent.retrosyn import official_composite

    # Sprint1 cundang weights (7:3 preliminary composite)
    assert official_composite(1.0, 0.0) == pytest.approx(0.7)
    assert official_composite(0.0, 1.0) == pytest.approx(0.3)
