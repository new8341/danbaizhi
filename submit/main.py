#!/usr/bin/env python3
"""Fusai docker entry — dispatch to track runner and pack submission."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import traceback
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent
if str(ROOT.parent) not in sys.path:
    sys.path.insert(0, str(ROOT.parent))

from submit.pack_submission import emit_error, move_to_saisresult, pack_directory
from submit.tracks.registry import get_runner


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Fusai track submission runner")
    p.add_argument(
        "--track",
        default=os.environ.get("FUSAI_TRACK", "danbaizhi"),
        help="Track id (default: env FUSAI_TRACK or danbaizhi)",
    )
    p.add_argument(
        "--saisdata",
        type=Path,
        default=Path(os.environ.get("SAISDATA", "/saisdata")),
        help="Read-only competition data root",
    )
    p.add_argument(
        "--saisresult",
        type=Path,
        default=Path(os.environ.get("SAISRESULT", "/saisresult")),
        help="Evaluation output directory",
    )
    p.add_argument(
        "--work-dir",
        type=Path,
        default=Path(os.environ.get("FUSAI_WORK_DIR", "/app")),
        help="Writable workspace inside container",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()
    request_id = str(uuid.uuid4())
    runner = get_runner(args.track)
    staging = args.work_dir / "submission_staging"
    local_zip = args.work_dir / runner.spec.output_name

    if staging.exists():
        shutil.rmtree(staging)
    staging.mkdir(parents=True, exist_ok=True)
    if local_zip.exists():
        local_zip.unlink()

    try:
        runner.run(args.saisdata, staging, args.work_dir)
        pack_directory(staging, local_zip)
        dest = args.saisresult / runner.spec.output_name
        move_to_saisresult(local_zip, dest)
        print(f"[OK] wrote {dest}", flush=True)
        return 0
    except subprocess.CalledProcessError as exc:
        emit_error(
            "TRACK_SUBPROCESS_FAILED",
            f"Track subprocess failed with exit code {exc.returncode}",
            request_id,
        )
    except SystemExit:
        raise
    except Exception as exc:
        print(traceback.format_exc(), flush=True)
        emit_error("TRACK_RUN_FAILED", str(exc), request_id)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
