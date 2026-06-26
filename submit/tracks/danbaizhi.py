"""Track 3 — protein conformation ensemble (Danbaizhi / Project)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
import os
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks._paths import danbaizhi_data_root, describe_saisdata
from submit.tracks.base import TrackRunner, TrackSpec


def _require_llm_config() -> list[str]:
    api_key = os.environ.get("LLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    base_url = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    provider = os.environ.get("LLM_PROVIDER") or "openai"
    if not api_key:
        emit_error(
            "DANBAIZHI_LLM_CONFIG_MISSING",
            "Missing required LLM/APIKEY environment variable: LLM_API_KEY or OPENAI_API_KEY",
        )
    masked = f"{api_key[:4]}...{api_key[-4:]}" if len(api_key) >= 8 else "***"
    return [
        "llm_config=required_by_semifinal_rules",
        f"llm_provider={provider}",
        f"llm_base_url={base_url}",
        f"llm_api_key_masked={masked}",
    ]


def _safe_fallback_enabled() -> bool:
    return os.environ.get("DANBAIZHI_SAFE_FALLBACK", "0").strip().lower() in {"1", "true", "yes"}


def _run_baseline_fallback(project_root: Path) -> None:
    cmd = [
        sys.executable,
        "code/generate_submission.py",
        "--problems-dir",
        "data",
        "--out-dir",
        "result",
        "--zip-name",
        "output.zip",
        "--strategy",
        "baseline_ca",
        "--seed",
        "42",
        "--note",
        "safe_fallback=baseline_ca_after_primary_failure",
    ]
    print("[Danbaizhi] primary failed; running safe baseline fallback", flush=True)
    print("[CMD]", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(project_root), check=True)


class DanbaizhiRunner(TrackRunner):
    spec = TrackSpec(
        name="danbaizhi",
        task_id="3",
        saisdata_hint="/saisdata/ or /saisdata/<id>/ (1.json, 2.json, 3.json)",
        output_name="submission.zip",
        output_members=("agent.log",),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        llm_logs = _require_llm_config()
        project_root = work_dir / "Project"
        if not (project_root / "code" / "main.py").is_file():
            emit_error(
                "DANBAIZHI_PROJECT_MISSING",
                f"Project bundle not found at {project_root}",
            )

        data_dir = project_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        data_root = danbaizhi_data_root(saisdata)
        print(f"[Danbaizhi] saisdata root={data_root}", flush=True)
        for name in ("1.json", "2.json", "3.json"):
            src = data_root / name
            if not src.is_file():
                emit_error(
                    "DANBAIZHI_INPUT_MISSING",
                    f"Missing input: {src}; data_root={data_root}; {describe_saisdata(saisdata)}",
                )
            shutil.copy2(src, data_dir / name)

        result_dir = project_root / "result"
        if result_dir.exists():
            shutil.rmtree(result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)

        cmd = [sys.executable, "code/main.py", "predict"]
        print("[CMD]", " ".join(cmd), flush=True)
        try:
            subprocess.run(cmd, cwd=str(project_root), check=True)
        except subprocess.CalledProcessError:
            if not _safe_fallback_enabled():
                raise
            _run_baseline_fallback(project_root)

        output_zip = result_dir / "output.zip"
        if not output_zip.is_file() and _safe_fallback_enabled():
            _run_baseline_fallback(project_root)
        if not output_zip.is_file():
            emit_error("DANBAIZHI_OUTPUT_MISSING", f"Predict did not create {output_zip}")

        staging_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip, "r") as zf:
            zf.extractall(staging_dir)
        agent_log = staging_dir / "agent.log"
        with agent_log.open("a", encoding="utf-8") as f:
            f.write("\n[semifinal_api_config]\n")
            f.write("\n".join(llm_logs) + "\n")
