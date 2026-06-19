"""Cylinder flow: run saisdata FNO inference."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from submit.tracks._paths import first_existing


def resolve_cylinder_test_path(saisdata: Path, problem_root: Path, board: str) -> Path | None:
    board = board.upper()
    if board == "A":
        return first_existing(problem_root / "data" / "cylinder_test_A.hdf5")
    return first_existing(
        saisdata / "66" / "cylinder_test_B.hdf5",
        problem_root / "data" / "cylinder_test_B.hdf5",
        saisdata / "cylinder_test_B.hdf5",
    )


def run_cylinder(
    problem_root: Path,
    out_path: Path,
    test_path: Path | None = None,
) -> tuple[str, list[str]]:
    logs: list[str] = []
    inference_dir = problem_root / "inference"
    run_script = inference_dir / "run_inference.py"
    test = test_path or (problem_root / "data" / "cylinder_test_A.hdf5")
    if not run_script.is_file() or not test.is_file():
        logs.append(f"[agent] cylinder_skip=inference_script_or_test_missing test={test}")
        return "missing", logs

    model = os.environ.get("SHENJING_MODEL", "fno")
    cmd = [
        sys.executable,
        str(run_script),
        "--model",
        model,
        "--test_path",
        str(test),
        "--pred_path",
        str(out_path),
    ]
    logs.append(f"[agent] cylinder_cmd={' '.join(cmd)}")
    try:
        subprocess.run(cmd, cwd=str(inference_dir), check=True)
    except (subprocess.CalledProcessError, OSError) as exc:
        logs.append(f"[agent] cylinder_inference_failed={exc}")
        return "failed", logs

    if out_path.is_file():
        logs.append(f"[agent] cylinder_source=inference model={model} test={test.name}")
        return "inference", logs
    logs.append("[agent] cylinder_inference_no_output")
    return "failed", logs
