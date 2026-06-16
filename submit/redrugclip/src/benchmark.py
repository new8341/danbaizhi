"""Load competition benchmark tasks from document/benchmark (read-only)."""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from src.paths import BENCHMARK_ROOT, MANIFEST_PATH


@dataclass(frozen=True)
class TaskInfo:
    task_id: str
    benchmark: str
    target: str
    task_type: str
    receptor_files: tuple[str, ...]
    reference_ligand_files: tuple[str, ...]
    ligand_file: str
    primary_metric: str
    num_receptors: int
    num_ligands: int

    @property
    def task_dir(self) -> Path:
        return BENCHMARK_ROOT / "tasks" / self.task_id

    def resolve(self, relative: str) -> Path:
        return self.task_dir / relative

    def receptor_paths(self) -> list[Path]:
        return [self.resolve(p) for p in self.receptor_files]

    def reference_ligand_paths(self) -> list[Path]:
        return [self.resolve(p) for p in self.reference_ligand_files]

    def ligands_csv_path(self) -> Path:
        return self.resolve(self.ligand_file)


def _parse_task_row(row: dict) -> TaskInfo:
    return TaskInfo(
        task_id=row["task_id"],
        benchmark=row["benchmark"],
        target=row["target"],
        task_type=row["task_type"],
        receptor_files=tuple(row["receptor_files"]),
        reference_ligand_files=tuple(row["reference_ligand_files"]),
        ligand_file=row["ligand_file"],
        primary_metric=row["primary_metric"],
        num_receptors=int(row["num_receptors"]),
        num_ligands=int(row["num_ligands"]),
    )


def load_manifest(manifest_path: Path | None = None) -> list[TaskInfo]:
    path = manifest_path or MANIFEST_PATH
    if not path.is_file():
        raise FileNotFoundError(f"manifest not found: {path}")

    tasks: list[TaskInfo] = []
    with path.open(encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
                tasks.append(_parse_task_row(row))
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                raise ValueError(f"invalid manifest line {line_no}: {e}") from e

    return tasks


class BenchmarkIndex:
    """Indexed view over all competition tasks."""

    def __init__(self, tasks: list[TaskInfo] | None = None):
        self.tasks = tasks if tasks is not None else load_manifest()
        self._by_id = {t.task_id: t for t in self.tasks}

    def __len__(self) -> int:
        return len(self.tasks)

    def __iter__(self) -> Iterator[TaskInfo]:
        return iter(self.tasks)

    def get(self, task_id: str) -> TaskInfo:
        if task_id not in self._by_id:
            raise KeyError(f"unknown task_id: {task_id}")
        return self._by_id[task_id]

    @property
    def total_ligands(self) -> int:
        return sum(t.num_ligands for t in self.tasks)

    def task_ids(self) -> list[str]:
        return [t.task_id for t in self.tasks]

    def iter_ligand_rows(self, task: TaskInfo) -> Iterator[dict[str, str]]:
        path = task.ligands_csv_path()
        if not path.is_file():
            raise FileNotFoundError(f"ligands.csv missing: {path}")
        with path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            if reader.fieldnames != ["ligand_id", "smiles"]:
                raise ValueError(
                    f"{path}: expected columns ligand_id,smiles; got {reader.fieldnames}"
                )
            for row in reader:
                yield row

    def count_ligands(self, task: TaskInfo) -> int:
        return sum(1 for _ in self.iter_ligand_rows(task))

    def validate_task_files(self, task: TaskInfo) -> list[str]:
        """Return list of missing paths (empty if all present)."""
        missing: list[str] = []
        if not task.ligands_csv_path().is_file():
            missing.append(str(task.ligands_csv_path()))
        for p in task.receptor_paths() + task.reference_ligand_paths():
            if not p.is_file():
                missing.append(str(p))
        return missing

    def validate_all_files(self) -> dict[str, list[str]]:
        return {t.task_id: self.validate_task_files(t) for t in self.tasks}
