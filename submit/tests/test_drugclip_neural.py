"""Tests for DrugCLIP LMDB + strategy resolution."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submit.tracks.drugclip_agent.benchmark import BenchmarkIndex
from submit.tracks.drugclip_agent.lmdb import build_mol_lmdb_from_rows, build_pocket_lmdb
from submit.tracks.drugclip_agent.pipeline import resolve_strategy
from submit.tracks.drugclip_agent.pocket import extract_task_pockets


def test_drugclip_lmdb_mini(tmp_path: Path) -> None:
    pytest.importorskip("rdkit")
    benchmark = ROOT / "submit" / "tests" / "fixtures" / "drugclip_mini"
    index = BenchmarkIndex(benchmark)
    task = index.get("mini_task")
    rows = list(index.iter_ligand_rows(task))
    mol_path = tmp_path / "mols.lmdb"
    n = build_mol_lmdb_from_rows(rows, mol_path, num_conf=1, workers=1)
    assert n == len(rows)
    assert mol_path.is_file()

    full_bench = ROOT / "documen" / "DrugClip" / "benchmark"
    if not (full_bench / "manifest.jsonl").is_file():
        pytest.skip("full benchmark not present for pocket LMDB test")
    full_index = BenchmarkIndex(full_bench)
    full_task = full_index.get("dude_ampc")
    pockets = extract_task_pockets(full_task)
    assert pockets[0].pocket_coordinates
    poc_path = tmp_path / "pocket.lmdb"
    assert build_pocket_lmdb(pockets, poc_path) == len(pockets)


def test_drugclip_strategy_fallback() -> None:
    import os

    os.environ["DRUGCLIP_STRATEGY"] = "hybrid_max_qed_v2"
    try:
        assert resolve_strategy() == "hybrid_max_qed_v2"
    finally:
        os.environ.pop("DRUGCLIP_STRATEGY", None)
