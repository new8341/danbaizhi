#!/usr/bin/env python3
"""Score all benchmark tasks with a fixed strategy (no agent search)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
from datetime import datetime

from agent.strategies import Strategy, default_strategy_grid, strategy_to_config
from src.benchmark import BenchmarkIndex
from src.paths import OUTPUTS_DIR
from src.submission import append_scores_csv, package_result_zip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strategy", default="hybrid_max_qed")
    parser.add_argument("--task-id", action="append")
    parser.add_argument("--output", default=str(OUTPUTS_DIR / "result.csv"))
    parser.add_argument("--package", action="store_true", help="Build result.zip after CSV")
    args = parser.parse_args()

    strategies = {s.name: s for s in default_strategy_grid()}
    if args.strategy not in strategies:
        print(f"Unknown strategy. Choose from: {list(strategies)}")
        return 1
    strategy = strategies[args.strategy]
    scorer, config = strategy_to_config(strategy)

    index = BenchmarkIndex()
    tasks = index.tasks
    if args.task_id:
        tasks = [t for t in tasks if t.task_id in args.task_id]

    csv_path = Path(args.output)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    if csv_path.is_file():
        try:
            csv_path.unlink()
        except PermissionError:
            csv_path = csv_path.with_name("result_run.csv")
            print(f"Warning: output locked, using {csv_path}")

    log_path = OUTPUTS_DIR / "result.log"
    with log_path.open("a", encoding="utf-8") as lf:
        lf.write(
            f"\nDirect inference {datetime.now().isoformat()} strategy={strategy.name} -> {csv_path}\n"
        )

    for i, task in enumerate(tasks, 1):
        print(f"[{i}/{len(tasks)}] {task.task_id} ({task.num_ligands} ligands)")
        rows = list(index.iter_ligand_rows(task))
        scores = scorer.score_task(task, rows, config)
        append_scores_csv(csv_path, task.task_id, scores, write_header=(i == 1))

    print(f"Wrote {csv_path}")
    if args.package:
        package_result_zip(csv_path, log_path)
        print(f"Wrote {OUTPUTS_DIR / 'result.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
