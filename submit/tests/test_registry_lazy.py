"""Ensure track runners load lazily (danbaizhi image has no rdkit)."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from submit.tracks.registry import get_runner


def test_danbaizhi_runner_lazy_import() -> None:
    for name in (
        "submit.tracks.baxiangfenzi",
        "submit.tracks.baxiangfenzi_agent.pipeline",
        "rdkit",
    ):
        sys.modules.pop(name, None)

    runner = get_runner("danbaizhi")
    assert runner.spec.name == "danbaizhi"
    assert "submit.tracks.baxiangfenzi" not in sys.modules
    assert "rdkit" not in sys.modules
