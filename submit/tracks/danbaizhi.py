"""Track 3 — protein conformation ensemble (Danbaizhi / Project)."""
from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks.base import TrackRunner, TrackSpec


class DanbaizhiRunner(TrackRunner):
    spec = TrackSpec(
        name="danbaizhi",
        task_id="3",
        saisdata_hint="/saisdata/ (1.json, 2.json, 3.json)",
        output_name="submission.zip",
        output_members=("agent.log",),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        project_root = work_dir / "Project"
        if not (project_root / "code" / "main.py").is_file():
            emit_error(
                "DANBAIZHI_PROJECT_MISSING",
                f"Project bundle not found at {project_root}",
            )

        data_dir = project_root / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        for name in ("1.json", "2.json", "3.json"):
            src = saisdata / name
            if not src.is_file():
                emit_error("DANBAIZHI_INPUT_MISSING", f"Missing input: {src}")
            shutil.copy2(src, data_dir / name)

        result_dir = project_root / "result"
        if result_dir.exists():
            shutil.rmtree(result_dir)
        result_dir.mkdir(parents=True, exist_ok=True)

        cmd = [sys.executable, "code/main.py", "predict"]
        print("[CMD]", " ".join(cmd), flush=True)
        subprocess.run(cmd, cwd=str(project_root), check=True)

        output_zip = result_dir / "output.zip"
        if not output_zip.is_file():
            emit_error("DANBAIZHI_OUTPUT_MISSING", f"Predict did not create {output_zip}")

        staging_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(output_zip, "r") as zf:
            zf.extractall(staging_dir)
