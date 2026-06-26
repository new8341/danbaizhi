"""DrugClip benchmark manifest and task metadata."""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator


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
    root: Path

    @property
    def task_dir(self) -> Path:
        return self.root / "tasks" / self.task_id

    def resolve(self, relative: str) -> Path:
        return self.task_dir / relative


def _parse_row(row: dict, root: Path) -> TaskInfo:
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
        root=root,
    )


class BenchmarkIndex:
    def __init__(self, benchmark_root: Path):
        self.root = benchmark_root
        manifest = benchmark_root / "manifest.jsonl"
        if not manifest.is_file():
            raise FileNotFoundError(f"manifest not found: {manifest}")
        self.tasks: list[TaskInfo] = []
        with manifest.open(encoding="utf-8") as mf:
            for line_no, line in enumerate(mf, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    self.tasks.append(_parse_row(json.loads(line), benchmark_root))
                except (json.JSONDecodeError, KeyError, TypeError) as exc:
                    raise ValueError(f"invalid manifest line {line_no}: {exc}") from exc
        self._by_id = {t.task_id: t for t in self.tasks}

    def get(self, task_id: str) -> TaskInfo:
        if task_id not in self._by_id:
            raise KeyError(f"unknown task_id: {task_id}")
        return self._by_id[task_id]

    def iter_ligand_rows(self, task: TaskInfo) -> Iterator[dict[str, str]]:
        path = task.resolve(task.ligand_file)
        if not path.is_file():
            raise FileNotFoundError(f"ligands missing: {path}")
        with path.open(newline="", encoding="utf-8") as lf:
            reader = csv.DictReader(lf)
            for row in reader:
                yield row
