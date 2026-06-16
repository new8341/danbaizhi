#!/usr/bin/env python3
"""
Package competition code submission (document/rull.md §2).

  python scripts/package_code_submission.py --team MyTeam --track drugclip

Creates <team>_<track>_submission.zip with src/, agent/, scripts/, configs/, run.sh, etc.
Excludes document/benchmark, outputs blobs, daima archives, .git.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent

INCLUDE_DIRS = ("src", "agent", "configs", "scripts", "external")
INCLUDE_FILES = (
    "README.md",
    "readme.md",
    "requirements.txt",
    "run.sh",
    "run.bat",
)

EXCLUDE_DIR_NAMES = {
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    "benchmark",
}
EXCLUDE_SUFFIXES = (".pyc", ".pyo")


def _should_skip(path: Path) -> bool:
    parts = path.parts
    if "document" in parts and "benchmark" in parts:
        return True
    if "outputs" in parts:
        return True
    if "daima" in parts:
        return True
    if "weights" in parts and path.suffix in (".pt", ".pth", ".bin", ".ckpt"):
        return True
    for name in EXCLUDE_DIR_NAMES:
        if name in parts:
            return True
    return path.suffix in EXCLUDE_SUFFIXES


def _add_path(zf: zipfile.ZipFile, path: Path, arc_prefix: str = "submission") -> None:
    if path.is_file():
        if _should_skip(path):
            return
        arc = f"{arc_prefix}/{path.relative_to(_ROOT).as_posix()}"
        zf.write(path, arc)
        return
    for child in sorted(path.rglob("*")):
        if child.is_dir():
            continue
        if _should_skip(child):
            continue
        arc = f"{arc_prefix}/{child.relative_to(_ROOT).as_posix()}"
        zf.write(child, arc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package team code submission zip")
    parser.add_argument("--team", required=True, help="Team name (teamname in zip filename)")
    parser.add_argument(
        "--team-id",
        help="Optional team ID; if set, zip filename uses ID instead of team name",
    )
    parser.add_argument("--track", default="drugclip", help="Track slug")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=_ROOT,
        help="Where to write the zip",
    )
    args = parser.parse_args()

    slug = args.team_id if args.team_id else args.team
    out_name = f"{slug}_{args.track}_submission.zip"
    out_path = Path(args.output_dir).resolve() / out_name

    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name in INCLUDE_FILES:
            p = _ROOT / name
            if p.is_file():
                _add_path(zf, p)
        for name in INCLUDE_DIRS:
            p = _ROOT / name
            if p.is_dir():
                _add_path(zf, p)
        # document/rull.md only (not full benchmark)
        rull = _ROOT / "document" / "rull.md"
        if rull.is_file():
            _add_path(zf, rull)

    print(f"Created {out_path} ({out_path.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"Team: {args.team}" + (f"  ID: {args.team_id}" if args.team_id else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
