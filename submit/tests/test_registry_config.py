"""Tests for submit/registry_config.py."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from submit.registry_config import image_ref, load_registry_env


def test_image_ref_default() -> None:
    ref = image_ref("danbaizhi", tag="0.1")
    assert ref.endswith("/ai4s-lee/danbaizhi:0.1")
    assert "crpi-" in ref or "aliyuncs.com" in ref


def test_image_ref_unknown_track() -> None:
    with pytest.raises(ValueError):
        image_ref("not_a_track")


def test_load_registry_env_from_file(tmp_path: Path) -> None:
    env_file = tmp_path / "registry.env"
    env_file.write_text(
        "REGISTRY=test.registry.example\nNAMESPACE=my-ns\nTAG=v9\n",
        encoding="utf-8",
    )
    cfg = load_registry_env(env_file)
    assert cfg["REGISTRY"] == "test.registry.example"
    assert cfg["NAMESPACE"] == "my-ns"
    assert cfg["TAG"] == "v9"
    assert (
        image_ref("drugclip", tag="v9", namespace="my-ns", registry="test.registry.example")
        == "test.registry.example/my-ns/drugclip:v9"
    )
