"""Track 4 — neural operator PDE (KS FNO + cylinder inference)."""
from __future__ import annotations

from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks.base import TrackRunner, TrackSpec
from submit.tracks.shenjingsuanzi_agent.pipeline import (
    CYLINDER_PRED_A,
    CYLINDER_PRED_B,
    KS_PRED_A,
    KS_PRED_B,
    run_agent,
)


class ShenjingsuanziRunner(TrackRunner):
    spec = TrackSpec(
        name="shenjingsuanzi",
        task_id="4",
        saisdata_hint="/saisdata/49/problem1+problem2; B榜 /saisdata/66/",
        output_name="submission.zip",
        output_members=(KS_PRED_A, CYLINDER_PRED_A, KS_PRED_B, CYLINDER_PRED_B),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        try:
            logs = run_agent(saisdata, staging_dir)
        except Exception as exc:
            emit_error("SHENJING_AGENT_FAILED", str(exc))

        log_path = work_dir / "shenjingsuanzi_run.log"
        log_path.write_text("\n".join(logs) + "\n", encoding="utf-8")
        for line in logs:
            if any(
                key in line
                for key in (
                    "ks_train_mount=",
                    "ks_train_path=",
                    "ks_source=",
                    "ks_phase=",
                    "ks_train_done",
                    "ks_train_shape=",
                    "ks_train_failed=",
                )
            ):
                print(line, flush=True)
        print(f"[Shenjingsuanzi] staged {KS_PRED_A}+{CYLINDER_PRED_A}+{KS_PRED_B}+{CYLINDER_PRED_B}", flush=True)
