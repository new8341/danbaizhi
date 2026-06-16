"""Build result.csv and result.zip for competition submission."""

from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from src.benchmark import BenchmarkIndex
from src.paths import OUTPUTS_DIR, PROJECT_ROOT

# Competition upload constraints (document/rull.md + platform rules)
SUBMIT_ZIP_NAME = "result.zip"
SUBMIT_CSV_NAME = "result.csv"
SUBMIT_LOG_NAME = "result.log"
MAX_ZIP_BYTES = 100 * 1024 * 1024  # 100 MB


def append_scores_csv(
    csv_path: Path,
    task_id: str,
    scores: dict[str, float],
    write_header: bool = False,
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "w" if write_header else "a"
    with csv_path.open(mode, newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header:
            w.writerow(["task_id", "ligand_id", "score"])
        for ligand_id, score in scores.items():
            w.writerow([task_id, ligand_id, f"{score:.6f}"])


def build_result_csv(
    all_scores: dict[str, dict[str, float]],
    out_path: Path | None = None,
) -> Path:
    out_path = out_path or OUTPUTS_DIR / "result.csv"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "ligand_id", "score"])
        for task_id in sorted(all_scores.keys()):
            for ligand_id, score in all_scores[task_id].items():
                w.writerow([task_id, ligand_id, f"{score:.6f}"])
    return out_path


def package_result_zip(
    csv_path: Path,
    log_path: Path,
    zip_path: Path | None = None,
    also_copy_to_root: bool = True,
) -> Path:
    """
    Build result.zip containing exactly result.csv and result.log (per rull.md).
    Default output: outputs/result.zip; also copies to project root result.zip for upload.
    """
    if not csv_path.is_file():
        raise FileNotFoundError(f"missing {SUBMIT_CSV_NAME}: {csv_path}")
    if not log_path.is_file():
        raise FileNotFoundError(f"missing {SUBMIT_LOG_NAME}: {log_path}")

    zip_path = zip_path or OUTPUTS_DIR / SUBMIT_ZIP_NAME
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()

    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, arcname=SUBMIT_CSV_NAME)
        zf.write(log_path, arcname=SUBMIT_LOG_NAME)

    size = zip_path.stat().st_size
    if size > MAX_ZIP_BYTES:
        raise ValueError(
            f"{zip_path.name} is {size / 1024 / 1024:.2f} MB; limit is 100 MB"
        )

    with zipfile.ZipFile(zip_path, "r") as zf:
        names = set(zf.namelist())
        required = {SUBMIT_CSV_NAME, SUBMIT_LOG_NAME}
        if names != required:
            raise ValueError(f"zip must contain only {required}; got {names}")

    if also_copy_to_root:
        root_zip = PROJECT_ROOT / SUBMIT_ZIP_NAME
        root_zip.write_bytes(zip_path.read_bytes())

    return zip_path


def merge_task_scores_into_index(
    index: BenchmarkIndex,
    task_scores: dict[str, dict[str, float]],
) -> dict[str, dict[str, float]]:
    """Ensure all tasks from benchmark are present."""
    full: dict[str, dict[str, float]] = {}
    for task in index:
        if task.task_id in task_scores:
            full[task.task_id] = task_scores[task.task_id]
        else:
            full[task.task_id] = {}
    return full
