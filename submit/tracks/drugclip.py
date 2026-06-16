"""Track 1 — DrugClip virtual screening (ReDrugClip hybrid_max_qed agent)."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
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


def _redrugclip_root(work_dir: Path) -> Path | None:
    for candidate in (
        Path("/app/ReDrugClip"),
        work_dir / "ReDrugClip",
        work_dir.parent / "ReDrugClip",
    ):
        if (candidate / "scripts" / "run_agent.py").is_file():
            return candidate
    return None


def _task_filter_args(benchmark: Path) -> list[str]:
    max_tasks = int(os.environ.get("DRUGCLIP_MAX_TASKS", "0"))
    if max_tasks <= 0:
        return []
    args: list[str] = []
    manifest = benchmark / "manifest.jsonl"
    count = 0
    with manifest.open(encoding="utf-8") as mf:
        for line in mf:
            line = line.strip()
            if not line:
                continue
            task_id = json.loads(line)["task_id"]
            args.extend(["--task-id", task_id])
            count += 1
            if count >= max_tasks:
                break
    return args


def _run_redrugclip(benchmark: Path, staging_dir: Path, work_dir: Path) -> bool:
    root = _redrugclip_root(work_dir)
    if root is None:
        return False

    strategy = os.environ.get("DRUGCLIP_STRATEGY", "hybrid_max_qed")
    env = os.environ.copy()
    env["BENCHMARK_ROOT"] = str(benchmark)
    (root / "outputs").mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(root / "scripts" / "run_agent.py"),
        "--fast",
        "--strategy",
        strategy,
        "--skip-archive",
        *_task_filter_args(benchmark),
    ]
    print("[DrugClip] ReDrugClip agent:", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(root), env=env, check=True)

    outputs = root / "outputs"
    for name in ("result.csv", "result.log"):
        src = outputs / name
        if not src.is_file():
            emit_error("DRUGCLIP_OUTPUT_MISSING", f"ReDrugClip did not produce {name}")
        shutil.copy2(src, staging_dir / name)
    return True


def _run_legacy_agent(benchmark: Path, staging_dir: Path) -> None:
    from submit.tracks.drugclip_agent.pipeline import run_benchmark, write_results

    max_tasks = int(os.environ.get("DRUGCLIP_MAX_TASKS", "0"))
    rows, logs = run_benchmark(benchmark, max_tasks=max_tasks)
    write_results(rows, staging_dir / "result.csv", staging_dir / "result.log", logs)
    tasks = len({r[0] for r in rows})
    print(f"[DrugClip] legacy agent wrote {len(rows)} scores for {tasks} tasks", flush=True)


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

        staging_dir.mkdir(parents=True, exist_ok=True)
        if not _run_redrugclip(benchmark, staging_dir, work_dir):
            _run_legacy_agent(benchmark, staging_dir)
        else:
            row_count = sum(1 for _ in (staging_dir / "result.csv").open(encoding="utf-8")) - 1
            print(f"[DrugClip] ReDrugClip hybrid agent wrote {row_count} scores", flush=True)
