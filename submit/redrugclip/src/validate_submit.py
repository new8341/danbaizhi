"""Validate competition submission result.csv / result.zip."""

from __future__ import annotations

import csv
import zipfile
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from src.benchmark import BenchmarkIndex, TaskInfo


REQUIRED_CSV_COLUMNS = ("task_id", "ligand_id", "score")


@dataclass
class ValidationReport:
    ok: bool = True
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    row_count: int = 0
    expected_rows: int = 0
    task_count: int = 0

    def add_error(self, msg: str) -> None:
        self.ok = False
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def _expected_pairs(index: BenchmarkIndex) -> dict[tuple[str, str], None]:
    expected: dict[tuple[str, str], None] = {}
    for task in index:
        for row in index.iter_ligand_rows(task):
            key = (task.task_id, row["ligand_id"])
            if key in expected:
                raise ValueError(f"duplicate ligand_id in benchmark: {key}")
            expected[key] = None
    return expected


def validate_result_csv(
    csv_path: Path,
    index: BenchmarkIndex | None = None,
) -> ValidationReport:
    report = ValidationReport()
    idx = index or BenchmarkIndex()
    report.task_count = len(idx)
    report.expected_rows = idx.total_ligands

    if not csv_path.is_file():
        report.add_error(f"result.csv not found: {csv_path}")
        return report

    try:
        expected = _expected_pairs(idx)
    except ValueError as e:
        report.add_error(str(e))
        return report

    seen: Counter[tuple[str, str]] = Counter()
    found_tasks: set[str] = set()

    with csv_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if tuple(reader.fieldnames or ()) != REQUIRED_CSV_COLUMNS:
            report.add_error(
                f"columns must be {REQUIRED_CSV_COLUMNS}; got {reader.fieldnames}"
            )
            return report

        for line_no, row in enumerate(reader, start=2):
            task_id = row.get("task_id", "").strip()
            ligand_id = row.get("ligand_id", "").strip()
            score_raw = row.get("score", "").strip()

            if not task_id or not ligand_id:
                report.add_error(f"line {line_no}: empty task_id or ligand_id")
                continue

            try:
                float(score_raw)
            except ValueError:
                report.add_error(f"line {line_no}: invalid score '{score_raw}'")
                continue

            key = (task_id, ligand_id)
            seen[key] += 1
            found_tasks.add(task_id)

            if key not in expected:
                report.add_error(f"line {line_no}: unknown pair ({task_id}, {ligand_id})")

    report.row_count = sum(seen.values())

    duplicates = [k for k, n in seen.items() if n > 1]
    if duplicates:
        sample = duplicates[:5]
        report.add_error(
            f"duplicate (task_id, ligand_id): {len(duplicates)} keys, e.g. {sample}"
        )

    missing = [k for k in expected if k not in seen]
    if missing:
        report.add_error(f"missing {len(missing)} pairs (expected full coverage)")
        if len(missing) <= 10:
            report.add_error(f"missing examples: {missing}")

    extra_tasks = found_tasks - set(idx.task_ids())
    if extra_tasks:
        report.add_error(f"unknown task_id in submission: {sorted(extra_tasks)[:10]}")

    for task in idx:
        if task.task_id not in found_tasks:
            report.add_error(f"task not covered: {task.task_id}")

    if report.row_count != report.expected_rows:
        report.add_error(
            f"row count {report.row_count} != expected {report.expected_rows}"
        )

    return report


def validate_result_zip(
    zip_path: Path,
    index: BenchmarkIndex | None = None,
) -> ValidationReport:
    report = ValidationReport()
    if not zip_path.is_file():
        report.add_error(f"result.zip not found: {zip_path}")
        return report

    try:
        with zipfile.ZipFile(zip_path, "r") as zf:
            names = set(zf.namelist())
            if "result.csv" not in names:
                report.add_error("result.zip must contain result.csv")
            if "result.log" not in names:
                report.add_error("result.zip must contain result.log")
            if report.errors:
                return report

            import tempfile

            with tempfile.TemporaryDirectory() as tmp:
                zf.extract("result.csv", tmp)
                csv_report = validate_result_csv(Path(tmp) / "result.csv", index)
                report.ok = csv_report.ok
                report.errors.extend(csv_report.errors)
                report.warnings.extend(csv_report.warnings)
                report.row_count = csv_report.row_count
                report.expected_rows = csv_report.expected_rows
                report.task_count = csv_report.task_count

            log_info = zf.getinfo("result.log")
            if log_info.file_size == 0:
                report.add_warning("result.log is empty")
    except zipfile.BadZipFile:
        report.add_error(f"invalid zip: {zip_path}")

    return report
