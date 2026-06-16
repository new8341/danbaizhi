#!/usr/bin/env python3
"""
Competition entry point (document/rull.md §4):
  python scripts/run_submit.py <input_dir> <output_dir>

Produces <output_dir>/result.zip with result.csv + result.log.
Default strategy: hybrid_max_qed (platform score 18.873261).
"""

from __future__ import annotations

import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse

from src.paths import OUTPUTS_DIR, PROJECT_ROOT


def main() -> int:
    parser = argparse.ArgumentParser(description="Run agent and write result.zip to output_dir")
    parser.add_argument("input_dir", help="Benchmark root (manifest.jsonl + tasks/)")
    parser.add_argument("output_dir", help="Directory for result.zip")
    parser.add_argument(
        "--strategy",
        default="hybrid_max_qed",
        help="Scoring strategy (default: platform champion)",
    )
    parser.add_argument(
        "--fuse",
        action="store_true",
        help="RRF-fuse champion CSV + v2 CSV instead of re-inference",
    )
    parser.add_argument("--skip-archive", action="store_true")
    parser.add_argument(
        "--no-reuse",
        action="store_true",
        help="Force full re-inference even if outputs/result.csv is already valid",
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir).resolve()
    output_dir = Path(args.output_dir).resolve()
    if not (input_dir / "manifest.jsonl").is_file():
        print(f"ERROR: manifest.jsonl not found in {input_dir}")
        return 1

    os.environ["BENCHMARK_ROOT"] = str(input_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.fuse:
        from src.fusion import load_scores, reciprocal_rank_fusion, write_fused_csv
        from src.submission import package_result_zip

        champ = PROJECT_ROOT / "daima" / "202605212027" / "results" / "result.csv"
        v2 = OUTPUTS_DIR / "result_v2.csv"
        if not champ.is_file():
            champ = OUTPUTS_DIR / "result.csv"
        if not v2.is_file():
            print("ERROR: need result_v2.csv for --fuse")
            return 1
        fused = reciprocal_rank_fusion(
            [load_scores(champ), load_scores(v2)],
            weights=[0.85, 0.15],
        )
        csv_path = OUTPUTS_DIR / "result_fusion.csv"
        write_fused_csv(fused, csv_path)
        log_path = OUTPUTS_DIR / "result.log"
        with log_path.open("a", encoding="utf-8") as lf:
            lf.write(
                f"\n[{datetime.now().isoformat()}] run_submit --fuse "
                f"RRF champion(0.85)+v2(0.15) -> {csv_path}\n"
            )
        package_result_zip(csv_path, log_path)
    else:
        cmd = [
            sys.executable,
            str(_ROOT / "scripts" / "run_agent.py"),
            "--fast",
            "--strategy",
            args.strategy,
        ]
        if not args.no_reuse:
            cmd.append("--reuse-if-valid")
        if args.skip_archive:
            cmd.append("--skip-archive")
        r = subprocess.run(cmd, cwd=str(_ROOT))
        if r.returncode != 0:
            return r.returncode

    src_zip = OUTPUTS_DIR / "result.zip"
    if not src_zip.is_file():
        src_zip = PROJECT_ROOT / "result.zip"
    if not src_zip.is_file():
        print("ERROR: result.zip not created")
        return 1

    dest = output_dir / "result.zip"
    dest.write_bytes(src_zip.read_bytes())
    for name in ("result.csv", "result.log"):
        src = OUTPUTS_DIR / name
        if src.is_file():
            (output_dir / name).write_bytes(src.read_bytes())

    print(f"Wrote {dest}")
    subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "validate_submission.py"), "--zip", str(dest)],
        cwd=str(_ROOT),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
