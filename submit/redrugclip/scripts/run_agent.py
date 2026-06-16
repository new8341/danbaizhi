#!/usr/bin/env python3
"""Run autonomous DrugCLIP optimization agent (full competition pipeline)."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse

from agent.runner import DrugClipAgent


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ReDrugClip autonomous agent")
    parser.add_argument("--pilot-only", action="store_true", help="Only pilot strategy search")
    parser.add_argument(
        "--fast",
        action="store_true",
        help="Skip strategy search; use baseline_fp_max (still logs all phases)",
    )
    parser.add_argument("--task-id", action="append", help="Limit to specific task(s)")
    parser.add_argument("--skip-archive", action="store_true")
    parser.add_argument("--config", type=str, default="configs/agent.yaml")
    parser.add_argument(
        "--strategy",
        help="Force strategy name (e.g. hybrid_max_qed); skips search if --fast",
    )
    parser.add_argument(
        "--reuse-if-valid",
        action="store_true",
        help="Skip full inference when outputs/result.csv already passes validation",
    )
    args = parser.parse_args()

    agent = DrugClipAgent(Path(args.config))
    zip_path = agent.run(
        pilot_only=args.pilot_only,
        tasks=args.task_id,
        skip_archive=args.skip_archive,
        fast=args.fast,
        forced_strategy=args.strategy,
        reuse_if_valid=args.reuse_if_valid,
    )
    if zip_path:
        print(f"Submission ready: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
