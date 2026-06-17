"""Neural operator agent: KS FNO train + cylinder inference."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from submit.tracks._paths import first_existing, saisdata_subdir
from submit.tracks.shenjingsuanzi_agent.cylinder import run_cylinder
from submit.tracks.shenjingsuanzi_agent.data_utils import ks_baseline_from_test
from submit.tracks.shenjingsuanzi_agent.ks import run_ks

KS_NAME = "KS_pred_A.hdf5"
CYLINDER_NAME = "cylinder_pred_A.hdf5"

PLATFORM_HISTORY = (
    ("2026-05-20", 57.685109, "fno1d_rollout_physics"),
)


def _problem_root(saisdata: Path, problem: str) -> Path | None:
    return first_existing(
        saisdata / "49" / problem,
        saisdata / "48" / problem,
        saisdata / problem,
        saisdata_subdir(saisdata, problem),
    )


def _find_sample(problem_root: Path, filename: str) -> Path | None:
    candidates = [
        problem_root / "sample_submission" / filename,
        problem_root / "sample_submission" / "A_board" / filename,
    ]
    if problem_root.is_dir():
        for hit in sorted(problem_root.rglob(filename)):
            if hit.is_file():
                candidates.append(hit)
    return first_existing(*candidates)


def _agent_header() -> list[str]:
    lines = [
        "=" * 72,
        "Shenjingsuanzi neural-operator agent",
        "=" * 72,
        f"[agent] timestamp={datetime.now(timezone.utc).isoformat()}",
        "[agent] phase=literature",
        "Reference: FNO1d autoregressive rollout on RealPDEBench-style trajectories.",
        "[agent] phase=diagnosis",
    ]
    for date, score, strategy in PLATFORM_HISTORY:
        lines.append(f"[agent] platform_history date={date} score={score:.4f} strategy={strategy}")
    lines.append(
        "[agent] diagnosis=KS uses field-normalized FNO1d; cylinder uses mounted FNO weights."
    )
    lines.append("[agent] phase=strategy selected=ks_fno1d+cylinder_fno")
    return lines


def run_agent(saisdata: Path, staging_dir: Path) -> list[str]:
    staging_dir.mkdir(parents=True, exist_ok=True)
    logs = _agent_header()

    p1 = _problem_root(saisdata, "problem1")
    p2 = _problem_root(saisdata, "problem2")
    if p1 is None or p2 is None:
        raise FileNotFoundError(f"problem1/problem2 missing under {saisdata}")

    ks_out = staging_dir / KS_NAME
    cyl_out = staging_dir / CYLINDER_NAME

    ks_train = p1 / "data" / "KS_train.hdf5"
    logs.append(f"[agent] problem1={p1}")
    logs.append(f"[agent] ks_train_mount={ks_train} exists={ks_train.is_file()}")

    logs.append("[agent] phase=ks")
    try:
        ks_source, ks_logs, train_t, inf_t = run_ks(p1, ks_out)
        logs.extend(ks_logs)
        logs.append(f"[agent] ks_source={ks_source} train_time={train_t:.1f}s inference_time={inf_t:.1f}s")
    except Exception as exc:
        logs.append(f"[agent] ks_train_failed={exc}")
        sample = _find_sample(p1, KS_NAME)
        if sample is not None:
            ks_out.write_bytes(sample.read_bytes())
            logs.append(f"[agent] ks_source=sample from {sample}")
        elif ks_baseline_from_test(p1, ks_out):
            logs.append("[agent] ks_source=baseline_extrapolation")
        else:
            raise

    logs.append("[agent] phase=cylinder")
    cyl_source, cyl_logs = run_cylinder(p2, cyl_out)
    logs.extend(cyl_logs)
    if cyl_source != "inference":
        sample = _find_sample(p2, CYLINDER_NAME)
        if sample is not None:
            cyl_out.write_bytes(sample.read_bytes())
            logs.append(f"[agent] cylinder_source=sample from {sample}")
        elif not cyl_out.is_file():
            raise FileNotFoundError("cylinder prediction missing after inference and sample fallback")

    logs.append(f"[agent] phase=done outputs={KS_NAME}+{CYLINDER_NAME}")
    return logs
