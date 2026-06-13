"""Track 1 — DrugClip virtual screening baseline (format-valid scaffold)."""
from __future__ import annotations

import csv
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks.base import TrackRunner, TrackSpec


def _benchmark_root(work_dir: Path) -> Path:
    env = os.environ.get("DRUGCLIP_BENCHMARK_ROOT")
    if env:
        return Path(env)
    for candidate in (work_dir / "benchmark", work_dir / "DrugClip" / "benchmark"):
        if candidate.is_dir():
            return candidate
    emit_error(
        "DRUGCLIP_BENCHMARK_MISSING",
        "Embed benchmark at /app/benchmark or set DRUGCLIP_BENCHMARK_ROOT",
    )


def _score(task_id: str, ligand_id: str) -> float:
    digest = hashlib.sha256(f"{task_id}:{ligand_id}".encode()).hexdigest()
    return round(int(digest[:8], 16) % 100000 / 100.0, 2)


class DrugclipRunner(TrackRunner):
    spec = TrackSpec(
        name="drugclip",
        task_id="1",
        saisdata_hint="benchmark embedded in image (not mounted)",
        output_name="result.zip",
        output_members=("result.csv", "result.log"),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        benchmark = _benchmark_root(work_dir)
        manifest = benchmark / "manifest.jsonl"
        if not manifest.is_file():
            emit_error("DRUGCLIP_MANIFEST_MISSING", f"Missing {manifest}")

        max_tasks = int(os.environ.get("DRUGCLIP_MAX_TASKS", "0"))
        staging_dir.mkdir(parents=True, exist_ok=True)
        csv_path = staging_dir / "result.csv"
        log_path = staging_dir / "result.log"

        rows = 0
        tasks = 0
        with csv_path.open("w", newline="", encoding="utf-8") as out_f:
            writer = csv.writer(out_f)
            writer.writerow(["task_id", "ligand_id", "score"])
            with manifest.open(encoding="utf-8") as mf:
                for line in mf:
                    line = line.strip()
                    if not line:
                        continue
                    meta = json.loads(line)
                    task_id = meta["task_id"]
                    ligands_path = benchmark / "tasks" / task_id / "ligands.csv"
                    if not ligands_path.is_file():
                        emit_error("DRUGCLIP_LIGANDS_MISSING", f"Missing {ligands_path}")
                    with ligands_path.open(encoding="utf-8") as lf:
                        reader = csv.DictReader(lf)
                        for row in reader:
                            writer.writerow([task_id, row["ligand_id"], _score(task_id, row["ligand_id"])])
                            rows += 1
                    tasks += 1
                    if max_tasks and tasks >= max_tasks:
                        break

        log_path.write_text(
            "\n".join(
                [
                    "DrugClip baseline scaffold",
                    f"timestamp={datetime.now(timezone.utc).isoformat()}",
                    f"benchmark={benchmark}",
                    f"tasks={tasks} rows={rows}",
                    "Replace with Agent-driven DrugCLIP inference before competition submit.",
                ]
            ),
            encoding="utf-8",
        )
        print(f"[DrugClip] wrote {rows} scores for {tasks} tasks", flush=True)
