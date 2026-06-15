"""Score all DrugClip benchmark tasks (parallel per task)."""
from __future__ import annotations

import csv
import json
import os
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

from submit.tracks.drugclip_agent.scoring import score_task


def _score_task_job(task_id: str, benchmark: str, ligands_rel: str) -> tuple[list[tuple[str, str, float]], list[str]]:
    task_dir = Path(benchmark) / "tasks" / task_id
    ligands_path = task_dir / ligands_rel if ligands_rel else task_dir / "ligands.csv"
    return score_task(task_id, task_dir, ligands_path)


def run_benchmark(benchmark: Path, max_tasks: int = 0) -> tuple[list[tuple[str, str, float]], list[str]]:
    manifest = benchmark / "manifest.jsonl"
    jobs: list[tuple[str, str]] = []
    header_logs = [
        "DrugClip RDKit fingerprint similarity agent",
        f"timestamp={datetime.now(timezone.utc).isoformat()}",
        f"benchmark={benchmark}",
        "phase=load_manifest",
    ]

    with manifest.open(encoding="utf-8") as mf:
        for line in mf:
            line = line.strip()
            if not line:
                continue
            meta = json.loads(line)
            task_id = meta["task_id"]
            ligands_rel = meta.get("ligand_file", "ligands.csv")
            jobs.append((task_id, ligands_rel))
            if max_tasks and len(jobs) >= max_tasks:
                break

    header_logs.append(f"phase=score tasks={len(jobs)}")
    workers = int(os.environ.get("DRUGCLIP_WORKERS", str(min(8, os.cpu_count() or 4))))

    all_rows: list[tuple[str, str, float]] = []
    all_logs = list(header_logs)

    if workers <= 1 or len(jobs) <= 1:
        for task_id, ligands_rel in jobs:
            rows, logs = _score_task_job(task_id, str(benchmark), ligands_rel)
            all_rows.extend(rows)
            all_logs.extend(logs)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_score_task_job, task_id, str(benchmark), ligands_rel): task_id
                for task_id, ligands_rel in jobs
            }
            for fut in as_completed(futures):
                task_id = futures[fut]
                rows, logs = fut.result()
                all_rows.extend(rows)
                all_logs.append(f"[agent] completed task={task_id} rows={len(rows)}")
                all_logs.extend(logs)

    all_logs.append(f"phase=done total_rows={len(all_rows)} workers={workers}")
    return all_rows, all_logs


def write_results(rows: list[tuple[str, str, float]], csv_path: Path, log_path: Path, logs: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as out_f:
        writer = csv.writer(out_f)
        writer.writerow(["task_id", "ligand_id", "score"])
        for task_id, ligand_id, score in rows:
            writer.writerow([task_id, ligand_id, score])
    log_path.write_text("\n".join(logs), encoding="utf-8")
