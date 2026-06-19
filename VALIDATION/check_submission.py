#!/usr/bin/env python3
"""Validate local submission zip against track contract."""
from __future__ import annotations

import argparse
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

AGENT_MARKERS = ("Stage 1", "Stage 2", "Stage 3", "理解", "[agent]")


def _check_danbaizhi(zf: zipfile.ZipFile) -> list[str]:
    errs: list[str] = []
    names = zf.namelist()
    for pid, n in ((1, 4), (2, 4), (3, 3)):
        for k in range(1, n + 1):
            want = f"{pid}_conf{k}_pred.cif"
            if want not in names:
                errs.append(f"missing {want}")
    if "agent.log" not in names:
        errs.append("missing agent.log")
    else:
        log = zf.read("agent.log").decode("utf-8", errors="replace")
        if not any(m in log for m in AGENT_MARKERS):
            errs.append("agent.log lacks stage markers")
    return errs


def _check_shenjingsuanzi(zf: zipfile.ZipFile) -> list[str]:
    errs: list[str] = []
    names = set(zf.namelist())
    for want in ("KS_pred_A.hdf5", "cylinder_pred_A.hdf5"):
        if want not in names:
            errs.append(f"missing {want}")
    return errs


def _check_drugclip(zf: zipfile.ZipFile) -> list[str]:
    errs: list[str] = []
    names = zf.namelist()
    for want in ("result.csv", "result.log"):
        if want not in names:
            errs.append(f"missing {want}")
    if "result.csv" in names:
        head = zf.read("result.csv").decode("utf-8", errors="replace").splitlines()[:2]
        if len(head) < 2 or "ligand_id" not in head[0].lower():
            errs.append("result.csv header unexpected")
    return errs


def _check_baxiangfenzi(zf: zipfile.ZipFile) -> list[str]:
    errs: list[str] = []
    for i in (1, 2, 3):
        want = f"result{i}.csv"
        if want not in zf.namelist():
            errs.append(f"missing {want}")
    return errs


CHECKERS = {
    "danbaizhi": _check_danbaizhi,
    "drugclip": _check_drugclip,
    "baxiangfenzi": _check_baxiangfenzi,
    "shenjingsuanzi": _check_shenjingsuanzi,
}


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate submission zip")
    parser.add_argument("--track", required=True, choices=sorted(CHECKERS))
    parser.add_argument("--zip", dest="zip_path", required=True, type=Path)
    args = parser.parse_args()
    zp = args.zip_path if args.zip_path.is_absolute() else ROOT / args.zip_path
    if not zp.is_file():
        print(f"check_submission: zip not found: {zp}", file=sys.stderr)
        return 1
    with zipfile.ZipFile(zp) as zf:
        errs = CHECKERS[args.track](zf)
    if errs:
        print(f"check_submission: FAIL track={args.track} zip={zp}", file=sys.stderr)
        for e in errs:
            print(f"  {e}", file=sys.stderr)
        return 1
    print(f"check_submission: OK track={args.track} zip={zp}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
