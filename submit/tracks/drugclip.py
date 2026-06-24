"""Track 1 — DrugClip virtual screening (hybrid_max_qed agent)."""
from __future__ import annotations

import os
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks.base import TrackRunner, TrackSpec
from submit.tracks.drugclip_agent.pipeline import run_benchmark, write_results


def _require_llm_config() -> list[str]:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    provider = os.environ.get("LLM_PROVIDER") or "openai"
    if not api_key:
        emit_error(
            "DRUGCLIP_LLM_CONFIG_MISSING",
            "Missing required LLM/APIKEY environment variable: LLM_API_KEY or OPENAI_API_KEY",
        )
    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) >= 8 else "***"
    return [
        "llm_config=required_by_semifinal_rules",
        f"llm_provider={provider}",
        f"llm_base_url={base_url}",
        f"llm_api_key_masked={masked}",
    ]


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
        llm_logs = _require_llm_config()
        benchmark = _benchmark_root(work_dir)
        manifest = benchmark / "manifest.jsonl"
        if not manifest.is_file():
            emit_error("DRUGCLIP_MANIFEST_MISSING", f"Missing {manifest}")

        max_tasks = int(os.environ.get("DRUGCLIP_MAX_TASKS", "0"))
        rows, logs = run_benchmark(benchmark, max_tasks=max_tasks)
        logs = llm_logs + logs

        staging_dir.mkdir(parents=True, exist_ok=True)
        write_results(rows, staging_dir / "result.csv", staging_dir / "result.log", logs)
        tasks = len({r[0] for r in rows})
        print(f"[DrugClip] wrote {len(rows)} scores for {tasks} tasks", flush=True)
