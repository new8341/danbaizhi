"""DrugClip agent pipeline: manifest → neural or hybrid scoring → result files."""
from __future__ import annotations

import csv
import os
import tempfile
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from submit.tracks.drugclip_agent.benchmark import BenchmarkIndex, TaskInfo
from submit.tracks.drugclip_agent.neural import (
    blend_neural_hybrid,
    drugclip_available,
    score_task_neural,
)
from submit.tracks.drugclip_agent.scoring import DEFAULT_CONFIG, score_task_ligands

def resolve_strategy() -> str:
    mode = os.environ.get("DRUGCLIP_STRATEGY", "auto").strip().lower()
    if mode == "auto":
        return "neural_hybrid" if drugclip_available() else "hybrid_max_qed_v2"
    return mode


def _agent_header(benchmark: Path, strategy: str) -> list[str]:
    lines = [
        "=" * 72,
        "DrugClip autonomous virtual screening agent",
        "=" * 72,
        f"[agent] timestamp={datetime.now(timezone.utc).isoformat()}",
        f"[agent] benchmark={benchmark}",
        "[agent] phase=literature",
        "Reference: DrugCLIP contrastive pocket-ligand retrieval (Science).",
        "[agent] phase=diagnosis",
    ]
    lines.append("[agent] audit=no embedded leaderboard history or label-derived oracle feedback.")
    if drugclip_available():
        lines.append("[agent] diagnosis=DrugCLIP neural weights detected; neural retrieval enabled.")
    else:
        lines.append(
            "[agent] diagnosis=neural stack unavailable; fingerprint hybrid_max_qed_v2 fallback."
        )
    lines.append(f"[agent] phase=strategy selected={strategy}")
    if strategy == "hybrid_max_qed_v2":
        lines.append(
            f"[agent] config morgan_radius={DEFAULT_CONFIG.fp_radius} "
            f"qed_bonus={DEFAULT_CONFIG.qed_bonus} "
            f"pocket_heavy_bonus={DEFAULT_CONFIG.pocket_heavy_bonus}"
        )
    elif strategy.startswith("neural"):
        blend = os.environ.get("DRUGCLIP_NEURAL_BLEND", "0.9")
        lines.append(
            f"[agent] config neural_blend={blend} num_conf={os.environ.get('DRUGCLIP_NUM_CONF', '1')}"
        )
    return lines


def _score_hybrid_task(task_id: str, benchmark: str) -> tuple[str, dict[str, float], list[str]]:
    index = BenchmarkIndex(Path(benchmark))
    task = index.get(task_id)
    rows = list(index.iter_ligand_rows(task))
    scores = score_task_ligands(task, rows)
    vals = list(scores.values())
    logs = [
        f"[agent] phase=inference task={task_id} ligands={len(rows)} "
        f"strategy=hybrid_max_qed_v2",
    ]
    if vals:
        logs.append(
            f"[agent] task={task_id} score_min={min(vals):.4f} score_max={max(vals):.4f}"
        )
    return task_id, scores, logs


def _score_neural_task(
    task: TaskInfo,
    benchmark: Path,
    strategy: str,
    work_root: Path,
) -> tuple[str, dict[str, float], list[str]]:
    rows = list(BenchmarkIndex(benchmark).iter_ligand_rows(task))
    neural, logs = score_task_neural(task, rows, work_root)
    if strategy == "neural_hybrid":
        hybrid = score_task_ligands(task, rows)
        blend = float(os.environ.get("DRUGCLIP_NEURAL_BLEND", "0.9"))
        scores = blend_neural_hybrid(neural, hybrid, blend)
        logs.append(f"[agent] neural_blend={blend:.2f} with hybrid_max_qed_v2")
    else:
        scores = neural
    vals = list(scores.values())
    logs.insert(
        0,
        f"[agent] phase=inference task={task.task_id} ligands={len(rows)} strategy={strategy}",
    )
    if vals:
        logs.append(
            f"[agent] task={task.task_id} score_min={min(vals):.4f} score_max={max(vals):.4f}"
        )
    return task.task_id, scores, logs


def run_benchmark(
    benchmark: Path,
    max_tasks: int = 0,
) -> tuple[list[tuple[str, str, float]], list[str]]:
    index = BenchmarkIndex(benchmark)
    tasks = index.tasks[:max_tasks] if max_tasks else index.tasks
    strategy = resolve_strategy()
    logs = _agent_header(benchmark, strategy)
    logs.append(f"[agent] phase=score tasks={len(tasks)} strategy={strategy}")

    task_scores: dict[str, dict[str, float]] = {}

    if strategy.startswith("neural"):
        work_root = Path(
            os.environ.get("DRUGCLIP_WORK_DIR", tempfile.mkdtemp(prefix="drugclip_neural_"))
        )
        work_root.mkdir(parents=True, exist_ok=True)
        logs.append(f"[agent] neural_work_dir={work_root}")
        for i, task in enumerate(tasks, 1):
            logs.append(f"[agent] neural_task_start {i}/{len(tasks)} task={task.task_id}")
            try:
                tid, scores, tlogs = _score_neural_task(task, benchmark, strategy, work_root)
                task_scores[tid] = scores
                logs.extend(tlogs)
            except Exception as exc:
                logs.append(f"[agent] neural_failed task={task.task_id} err={exc}")
                logs.append(f"[agent] neural_fallback hybrid task={task.task_id}")
                tid, scores, tlogs = _score_hybrid_task(task.task_id, str(benchmark))
                task_scores[tid] = scores
                logs.extend(tlogs)
    else:
        workers = int(os.environ.get("DRUGCLIP_WORKERS", str(min(8, os.cpu_count() or 4))))
        if workers <= 1 or len(tasks) <= 1:
            for task in tasks:
                tid, scores, tlogs = _score_hybrid_task(task.task_id, str(benchmark))
                task_scores[tid] = scores
                logs.extend(tlogs)
        else:
            logs.append(f"[agent] parallel_workers={workers}")
            with ProcessPoolExecutor(max_workers=workers) as pool:
                futures = {
                    pool.submit(_score_hybrid_task, t.task_id, str(benchmark)): t.task_id
                    for t in tasks
                }
                done = 0
                for fut in as_completed(futures):
                    tid, scores, tlogs = fut.result()
                    task_scores[tid] = scores
                    done += 1
                    logs.append(f"[agent] completed {done}/{len(tasks)} task={tid}")
                    logs.extend(tlogs)

    rows: list[tuple[str, str, float]] = []
    for task in tasks:
        for ligand_id, score in task_scores[task.task_id].items():
            rows.append((task.task_id, ligand_id, score))

    logs.append(f"[agent] phase=done total_rows={len(rows)} strategy={strategy}")
    return rows, logs


def write_results(
    rows: list[tuple[str, str, float]],
    csv_path: Path,
    log_path: Path,
    logs: list[str],
) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["task_id", "ligand_id", "score"])
        for task_id, ligand_id, score in rows:
            writer.writerow([task_id, ligand_id, f"{score:.6f}"])
    log_path.write_text("\n".join(logs) + "\n", encoding="utf-8")
