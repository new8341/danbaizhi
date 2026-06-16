#!/usr/bin/env python3
"""Archive competition run: code snapshot + score metadata under guidang/YYYYMMDDHHMM/."""
from __future__ import annotations

import argparse
import io
import json
import shutil
import subprocess
import tarfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

TRACK_CODE = {
    "drugclip": [
        "submit/tracks/drugclip.py",
        "submit/tracks/drugclip_agent",
        "submit/Dockerfile.drugclip",
    ],
    "shenjingsuanzi": [
        "submit/tracks/shenjingsuanzi.py",
        "submit/tracks/shenjingsuanzi_agent",
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


def _copy_paths_from_git(dest: Path, rel_paths: list[str], commit: str) -> None:
    """Snapshot track code as it existed at a git commit (for scored submissions)."""
    existing: list[str] = []
    for rel in rel_paths:
        ls = subprocess.run(
            ["git", "ls-tree", commit, rel],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        if ls.returncode == 0 and ls.stdout.strip():
            existing.append(rel)
    if not existing:
        return
    data = subprocess.check_output(["git", "archive", commit, *existing], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:") as tar:
        if hasattr(tarfile, "data_filter"):
            tar.extractall(dest, filter="data")
        else:
            tar.extractall(dest)


def archive_run(
    stamp: str,
    track: str,
    score: float,
    note: str = "",
    extra: dict | None = None,
    git_commit: str = "",
) -> Path:
    out = ROOT / "guidang" / stamp / track
    out.mkdir(parents=True, exist_ok=True)
    code_commit = git_commit.strip() or _git_head()
    meta = {
        "track": track,
        "score": score,
        "stamp": stamp,
        "archived_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": code_commit,
        "note": note,
    }
    if extra:
        meta.update(extra)
    (out / "score_meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rel_paths = TRACK_CODE.get(track, [])
    if git_commit.strip():
        _copy_paths_from_git(out, rel_paths, git_commit.strip())
    else:
        _copy_paths(out, rel_paths)
    return out


def update_cundang(
    track: str,
    score: float,
    stamp: str,
    note: str = "",
    git_commit: str = "",
) -> Path:
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
    rel_paths = TRACK_CODE.get(track, [])
    code_commit = git_commit.strip() or _git_head()
    if git_commit.strip():
        _copy_paths_from_git(cundang, rel_paths, code_commit)
    else:
        _copy_paths(cundang, rel_paths)
    meta = {
        "track": track,
        "score": score,
        "stamp": stamp,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
        "git_commit": code_commit,
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
    parser.add_argument(
        "--git-commit",
        default="",
        help="Archive code from this commit (default: current working tree)",
    )
    args = parser.parse_args()

    out = archive_run(
        args.stamp, args.track, args.score, args.note, git_commit=args.git_commit
    )
    print(f"guidang -> {out}")
    if not args.no_cundang:
        c = update_cundang(
            args.track, args.score, args.stamp, args.note, git_commit=args.git_commit
        )
        print(f"cundang -> {c}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
