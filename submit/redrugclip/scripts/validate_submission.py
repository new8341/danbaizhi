#!/usr/bin/env python3
"""Validate result.csv or result.zip against the competition benchmark."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
import json

from src.benchmark import BenchmarkIndex
from src.validate_submit import validate_result_csv, validate_result_zip


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate submission files")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", type=str, help="Path to result.csv")
    group.add_argument("--zip", type=str, help="Path to result.zip")
    parser.add_argument("--json", action="store_true", help="Print report as JSON")
    args = parser.parse_args()

    index = BenchmarkIndex()
    if args.csv:
        report = validate_result_csv(Path(args.csv), index)
    else:
        report = validate_result_zip(Path(args.zip), index)

    if args.json:
        print(
            json.dumps(
                {
                    "ok": report.ok,
                    "errors": report.errors,
                    "warnings": report.warnings,
                    "row_count": report.row_count,
                    "expected_rows": report.expected_rows,
                    "task_count": report.task_count,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"ok={report.ok} rows={report.row_count}/{report.expected_rows}")
        for w in report.warnings:
            print(f"WARN: {w}")
        for e in report.errors:
            print(f"ERROR: {e}")

    return 0 if report.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
