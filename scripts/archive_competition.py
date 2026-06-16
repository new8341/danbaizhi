#!/usr/bin/env python3
"""Archive competition run: code snapshot + score metadata under guidang/YYYYMMDDHHMM/."""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TRACK_CODE = {
    "drugclip": [
        "submit/tracks/drugclip.py",
        "submit/tracks/drugclip_agent",
        "submit/redrugclip",
        "submit/Dockerfile.drugclip",
    ],
    "shenjingsuanzi": [
        "submit/tracks/shenjingsuanzi.py",
        "shenjingsuanzi/pdeburgers",
        "submit/Dockerfile.shenjingsuanzi",
    ],
    "baxiangfenzi": [
        "submit/tracks/baxiangfenzi.py",
        "submit/tracks/baxiangfenzi_agent",
        "submit/Dockerfile.baxiangfenzi",
    ],
    "danbaizhi": [
        "submit/tracks/danbaizhi.py",
        "Project",
        "submit/Dockerfile.danbaizhi",
    ],
}


def _git_head() -> str:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True
        ).strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _copy_paths(dest: Path, rel_paths: list[str]) -> None:
    for rel in rel_paths:
        src = ROOT / rel
        if not src.exists():
            continue
        dst = dest / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            if dst.exists():
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
        else:
            shutil.copy2(src, dst)


def archive_run(
    stamp: str,
    track: str,
    score: float,
    note: str = "",
    extra: dict | None = None,
) -> Path:
    out = ROOT / "guidang" / stamp / track
    out.mkdir(parents=True, exist_ok=True)
    meta = {
        "track": track,
        "score": score,
        "stamp": stamp,
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_head(),
        "note": note,
    }
    if extra:
        meta.update(extra)
    (out / "score_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    _copy_paths(out, TRACK_CODE.get(track, []))
    return out


def update_cundang(track: str, score: float, stamp: str, note: str = "") -> Path:
    """Update cundang/<track>/ if score improves."""
    cundang = ROOT / "cundang" / track
    cundang.mkdir(parents=True, exist_ok=True)
    meta_path = cundang / "best.json"
    prev = 0.0
    if meta_path.is_file():
        prev = float(json.loads(meta_path.read_text(encoding="utf-8")).get("score", 0.0))
    if score <= prev:
        return cundang
    if cundang.exists():
        for child in cundang.iterdir():
            if child.name == "best.json":
                continue
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    _copy_paths(cundang, TRACK_CODE.get(track, []))
    meta = {
        "track": track,
        "score": score,
        "stamp": stamp,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": _git_head(),
        "note": note,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return cundang


def main() -> int:
    parser = argparse.ArgumentParser(description="Archive guidang + update cundang")
    parser.add_argument("--stamp", required=True, help="YYYYMMDDHHMM from platform score time")
    parser.add_argument("--track", required=True)
    parser.add_argument("--score", type=float, required=True)
    parser.add_argument("--note", default="")
    parser.add_argument("--no-cundang", action="store_true")
    args = parser.parse_args()

    out = archive_run(args.stamp, args.track, args.score, args.note)
    print(f"guidang -> {out}")
    if not args.no_cundang:
        c = update_cundang(args.track, args.score, args.stamp, args.note)
        print(f"cundang -> {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
