"""Tests for /saisdata path resolution."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submit.tracks._paths import danbaizhi_data_root


def test_danbaizhi_data_root_flat(tmp_path: Path) -> None:
    saisdata = tmp_path / "saisdata"
    saisdata.mkdir()
    for name in ("1.json", "2.json", "3.json"):
        (saisdata / name).write_text("{}", encoding="utf-8")
    assert danbaizhi_data_root(saisdata) == saisdata


def test_danbaizhi_data_root_nested_mount(tmp_path: Path) -> None:
    saisdata = tmp_path / "saisdata"
    nested = saisdata / "3"
    nested.mkdir(parents=True)
    for name in ("1.json", "2.json", "3.json"):
        (nested / name).write_text("{}", encoding="utf-8")
    assert danbaizhi_data_root(saisdata) == nested


def test_danbaizhi_data_root_auto_discover(tmp_path: Path) -> None:
    saisdata = tmp_path / "saisdata"
    nested = saisdata / "dataset_x"
    nested.mkdir(parents=True)
    for name in ("1.json", "2.json", "3.json"):
        (nested / name).write_text("{}", encoding="utf-8")
    assert danbaizhi_data_root(saisdata) == nested


def test_danbaizhi_data_root_deep_nested(tmp_path: Path) -> None:
    saisdata = tmp_path / "saisdata"
    nested = saisdata / "mount" / "batch" / "data"
    nested.mkdir(parents=True)
    for name in ("1.json", "2.json", "3.json"):
        (nested / name).write_text("{}", encoding="utf-8")
    assert danbaizhi_data_root(saisdata) == nested
