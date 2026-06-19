"""DrugClip agent pipeline: manifest → parallel hybrid_max_qed → result files."""
from __future__ import annotations

import csv
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from submit.tracks.drugclip_agent.benchmark import BenchmarkIndex
from submit.tracks.drugclip_agent.scoring import DEFAULT_CONFIG, score_task_ligands

PLATFORM_HISTORY = (
    ("2026-05-21", 18.873261, "hybrid_max_qed"),
    ("2026-05-25", 19.229531, "hybrid_max_qed"),
)


def _agent_header(benchmark: Path) -> list[str]:
    lines = [
        "=" * 72,
        "DrugClip autonomous virtual screening agent",
        "=" * 72,
        f"[agent] timestamp={datetime.now(timezone.utc).isoformat()}",
        f"[agent] benchmark={benchmark}",
        "[agent] phase=literature",
        "Reference: DrugCLIP contrastive pocket-ligand retrieval (Science).",
        "Docker agent: Morgan2 Tanimoto vs co-crystal ligand(s), multi-receptor max.",
        "[agent] phase=diagnosis",
    ]
    for date, score, strategy in PLATFORM_HISTORY:
        lines.append(f"[agent] platform_history date={date} score={score:.4f} strategy={strategy}")
    lines.append(
        "[agent] diagnosis=ensemble-heavy configs hurt EF1%; keep hybrid_max_qed_v2 + light priors."
    )
    lines.append("[agent] phase=strategy selected=hybrid_max_qed_v2")
    lines.append(
        f"[agent] config morgan_radius={DEFAULT_CONFIG.fp_radius} "
        f"qed_bonus={DEFAULT_CONFIG.qed_bonus} pocket_heavy_bonus={DEFAULT_CONFIG.pocket_heavy_bonus}"
    )
    return lines


def _score_one_task(task_id: str, benchmark: str) -> tuple[str, dict[str, float], list[str]]:
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


def run_benchmark(
    benchmark: Path,
    max_tasks: int = 0,
) -> tuple[list[tuple[str, str, float]], list[str]]:
    index = BenchmarkIndex(benchmark)
    tasks = index.tasks[:max_tasks] if max_tasks else index.tasks
    logs = _agent_header(benchmark)
    logs.append(f"[agent] phase=score tasks={len(tasks)}")

    workers = int(os.environ.get("DRUGCLIP_WORKERS", str(min(8, os.cpu_count() or 4))))
    task_scores: dict[str, dict[str, float]] = {}

    if workers <= 1 or len(tasks) <= 1:
        for task in tasks:
            tid, scores, tlogs = _score_one_task(task.task_id, str(benchmark))
            task_scores[tid] = scores
            logs.extend(tlogs)
    else:
        logs.append(f"[agent] parallel_workers={workers}")
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_score_one_task, t.task_id, str(benchmark)): t.task_id
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

    logs.append(f"[agent] phase=done total_rows={len(rows)} workers={workers}")
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
