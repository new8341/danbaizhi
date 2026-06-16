#!/usr/bin/env python3
"""Verify all benchmark task files exist and ligand counts match manifest."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse

from src.benchmark import BenchmarkIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate benchmark file integrity")
    parser.add_argument(
        "--count-ligands",
        action="store_true",
        help="Re-count ligands.csv rows (slower, full check)",
    )
    args = parser.parse_args()

    index = BenchmarkIndex()
    missing_any = False
    count_mismatch = []

    for task in index:
        missing = index.validate_task_files(task)
        if missing:
            missing_any = True
            print(f"[MISSING] {task.task_id}")
            for p in missing:
                print(f"  {p}")

        if args.count_ligands:
            actual = index.count_ligands(task)
            if actual != task.num_ligands:
                count_mismatch.append((task.task_id, task.num_ligands, actual))

    print(f"\nSummary: {len(index)} tasks, {index.total_ligands} ligands (manifest)")
    if missing_any:
        print("Status: FAIL — missing files")
        return 1
    if count_mismatch:
        for tid, expected, actual in count_mismatch[:20]:
            print(f"[COUNT] {tid}: manifest={expected} actual={actual}")
        print(f"Status: FAIL — {len(count_mismatch)} count mismatches")
        return 1
    print("Status: OK — all referenced files present")
    if not args.count_ligands:
        print("Tip: run with --count-ligands for full row-count verification")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
