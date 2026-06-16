#!/usr/bin/env python3
"""Print benchmark task summary from manifest.jsonl."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse

from src.benchmark import BenchmarkIndex


def main() -> int:
    parser = argparse.ArgumentParser(description="List competition benchmark tasks")
    parser.add_argument(
        "--benchmark",
        choices=("DUD-E", "LIT-PCBA", "all"),
        default="all",
        help="Filter by benchmark name",
    )
    parser.add_argument("--task-id", help="Show details for one task")
    args = parser.parse_args()

    index = BenchmarkIndex()
    tasks = index.tasks
    if args.benchmark != "all":
        tasks = [t for t in tasks if t.benchmark == args.benchmark]
    if args.task_id:
        tasks = [index.get(args.task_id)]

    print(f"tasks={len(tasks)} total_ligands={sum(t.num_ligands for t in tasks)}")
    print(f"{'task_id':<24} {'benchmark':<12} {'ligands':>8} {'receptors':>10}")
    print("-" * 58)
    for t in tasks:
        print(
            f"{t.task_id:<24} {t.benchmark:<12} {t.num_ligands:>8} {t.num_receptors:>10}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
