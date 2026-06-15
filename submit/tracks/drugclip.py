"""Track 1 — DrugClip virtual screening (RDKit fingerprint similarity agent)."""
from __future__ import annotations

import os
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks.base import TrackRunner, TrackSpec
from submit.tracks.drugclip_agent.pipeline import run_benchmark, write_results


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
        rows, logs = run_benchmark(benchmark, max_tasks=max_tasks)

        staging_dir.mkdir(parents=True, exist_ok=True)
        write_results(rows, staging_dir / "result.csv", staging_dir / "result.log", logs)
        tasks = len({r[0] for r in rows})
        print(f"[DrugClip] wrote {len(rows)} scores for {tasks} tasks", flush=True)
