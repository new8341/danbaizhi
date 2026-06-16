"""Parallel per-task scoring for Docker time budget."""
from __future__ import annotations


def score_task_by_id(task_id: str, strategy_name: str) -> tuple[str, dict[str, float]]:
    from agent.strategies import default_strategy_grid, strategy_to_config
    from src.benchmark import BenchmarkIndex

    strategies = {s.name: s for s in default_strategy_grid()}
    strategy = strategies[strategy_name]
    scorer, config = strategy_to_config(strategy)
    index = BenchmarkIndex()
    task = index.get(task_id)
    rows = list(index.iter_ligand_rows(task))
    return task_id, scorer.score_task(task, rows, config)
