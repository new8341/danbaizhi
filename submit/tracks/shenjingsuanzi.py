"""Track 4 — neural operator PDE (KS + cylinder) baseline scaffold."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks._paths import first_existing, saisdata_subdir
from submit.tracks.base import TrackRunner, TrackSpec

KS_NAME = "KS_pred_A.hdf5"
CYLINDER_NAME = "cylinder_pred_A.hdf5"


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


def _seed_from_sample(problem_root: Path, staging_dir: Path, filename: str) -> bool:
    sample = _find_sample(problem_root, filename)
    if sample is not None:
        shutil.copy2(sample, staging_dir / filename)
        return True
    return False


def _ks_baseline_from_test(problem_root: Path, out_path: Path) -> bool:
    """Build KS_pred_A.hdf5 from test input when sample_submission is empty."""
    import h5py
    import numpy as np

    data_dir = problem_root / "data"
    test_path = first_existing(
        data_dir / "KS_test_A.hdf5",
        data_dir / "KS_test.hdf5",
    )
    if test_path is None and data_dir.is_dir():
        for hit in sorted(data_dir.glob("KS_test*.hdf5")):
            test_path = hit
            break
    if test_path is None or not test_path.is_file():
        return False

    with h5py.File(test_path, "r") as src:
        obs = np.asarray(src["tensor"], dtype=np.float32)
        t_obs = np.asarray(src["t-coordinate"], dtype=np.float32) if "t-coordinate" in src else None
        x_coord = np.asarray(src["x-coordinate"], dtype=np.float32) if "x-coordinate" in src else None

    n_samples, n_obs, n_x = obs.shape
    n_total = 400
    pred = np.zeros((n_samples, n_total, n_x), dtype=np.float16)
    pred[:, :n_obs] = obs.astype(np.float16)
    pred[:, n_obs:] = obs[:, -1:, :].astype(np.float16)

    with h5py.File(out_path, "w") as dst:
        dst.create_dataset("tensor", data=pred, dtype=np.float16)
        if t_obs is not None and len(t_obs) == n_obs:
            t_full = np.linspace(float(t_obs[0]), float(t_obs[-1]) + (n_total - n_obs) * 0.5, n_total)
            dst.create_dataset("t-coordinate", data=t_full.astype(np.float16))
        if x_coord is not None:
            dst.create_dataset("x-coordinate", data=x_coord.astype(np.float16))

    print(f"[Shenjingsuanzi] KS baseline from {test_path} -> {out_path}", flush=True)
    return True


def _run_problem2_inference(problem_root: Path, staging_dir: Path, pred_path: Path) -> bool:
    inference_dir = problem_root / "inference"
    run_script = inference_dir / "run_inference.py"
    if not run_script.is_file():
        return False

    test_path = problem_root / "data" / "cylinder_test_A.hdf5"
    if not test_path.is_file():
        return False

    model = os.environ.get("SHENJING_MODEL", "fno")
    cmd = [
        sys.executable,
        str(run_script),
        "--model",
        model,
        "--test_path",
        str(test_path),
        "--pred_path",
        str(pred_path),
    ]
    print("[CMD]", " ".join(cmd), flush=True)
    try:
        subprocess.run(cmd, cwd=str(inference_dir), check=True)
        return pred_path.is_file()
    except (subprocess.CalledProcessError, OSError) as exc:
        print(f"[WARN] problem2 inference failed: {exc}", flush=True)
        return False


class ShenjingsuanziRunner(TrackRunner):
    spec = TrackSpec(
        name="shenjingsuanzi",
        task_id="4",
        saisdata_hint="/saisdata/49/problem1 + problem2",
        output_name="submission.zip",
        output_members=(KS_NAME, CYLINDER_NAME),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        staging_dir.mkdir(parents=True, exist_ok=True)
        log = work_dir / "shenjingsuanzi_run.log"
        lines = [
            "Shenjingsuanzi baseline scaffold",
            f"timestamp={datetime.now(timezone.utc).isoformat()}",
        ]

        p1 = _problem_root(saisdata, "problem1")
        p2 = _problem_root(saisdata, "problem2")
        if p1 is None or p2 is None:
            emit_error(
                "SHENJING_PROBLEM_MISSING",
                f"Need problem1 and problem2 under saisdata; got p1={p1} p2={p2}",
            )

        ks_out = staging_dir / KS_NAME
        cyl_out = staging_dir / CYLINDER_NAME

        if not _seed_from_sample(p1, staging_dir, KS_NAME):
            if not _ks_baseline_from_test(p1, ks_out):
                emit_error("SHENJING_KS_SAMPLE_MISSING", f"No sample for {KS_NAME} under {p1}")
            lines.append(f"ks_source=baseline from {p1}/data")
        else:
            lines.append(f"ks_source=sample from {p1}")

        if not _run_problem2_inference(p2, staging_dir, cyl_out):
            if not _seed_from_sample(p2, staging_dir, CYLINDER_NAME):
                emit_error(
                    "SHENJING_CYLINDER_MISSING",
                    f"Inference failed and no sample for {CYLINDER_NAME} under {p2}",
                )
            lines.append(f"cylinder_source=sample from {p2}")
        else:
            lines.append(f"cylinder_source=inference model={os.environ.get('SHENJING_MODEL', 'fno')}")

        log.write_text("\n".join(lines), encoding="utf-8")
        print(f"[Shenjingsuanzi] staged {KS_NAME} + {CYLINDER_NAME}", flush=True)
