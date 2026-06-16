"""Track 4 — neural operator PDE (KS FNO + cylinder inference)."""
from __future__ import annotations

from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks.base import TrackRunner, TrackSpec
from submit.tracks.shenjingsuanzi_agent.pipeline import KS_NAME, CYLINDER_NAME, run_agent


class ShenjingsuanziRunner(TrackRunner):
    spec = TrackSpec(
        name="shenjingsuanzi",
        task_id="4",
        saisdata_hint="/saisdata/49/problem1 + problem2",
        output_name="submission.zip",
        output_members=(KS_NAME, CYLINDER_NAME),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        try:
            logs = run_agent(saisdata, staging_dir)
        except Exception as exc:
            emit_error("SHENJING_AGENT_FAILED", str(exc))

        log_path = work_dir / "shenjingsuanzi_run.log"
        log_path.write_text("\n".join(logs) + "\n", encoding="utf-8")
        print(f"[Shenjingsuanzi] staged {KS_NAME} + {CYLINDER_NAME}", flush=True)
