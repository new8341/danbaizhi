#!/usr/bin/env python3
"""
Archive current code + run outputs to daima/YYYYMMDDHHMM per competition rules.

Usage:
  python scripts/archive_run.py
  python scripts/archive_run.py --stamp 202605202200 --note "baseline inference"
  python scripts/archive_run.py --include outputs/result.csv outputs/result.log
"""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
import shutil
from datetime import datetime

from src.paths import (
    ARCHIVE_CODE_DIRS,
    ARCHIVE_ROOT_FILES,
    DAIMA_DIR,
    OUTPUTS_DIR,
    PROJECT_ROOT,
)


def archive_stamp() -> str:
    return datetime.now().strftime("%Y%m%d%H%M")


def _copy_tree(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(
            src,
            dst,
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", ".pytest_cache"),
        )
    elif src.is_file():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def create_archive(
    dest: Path,
    extra_paths: list[Path] | None = None,
    note: str | None = None,
) -> Path:
    dest.mkdir(parents=True, exist_ok=False)

    meta = dest / "archive_meta.txt"
    lines = [
        f"created_at={datetime.now().isoformat()}",
        f"project_root={PROJECT_ROOT}",
    ]
    if note:
        lines.append(f"note={note}")
    meta.write_text("\n".join(lines) + "\n", encoding="utf-8")

    code_dir = dest / "code"
    code_dir.mkdir()
    for name in ARCHIVE_CODE_DIRS:
        src = PROJECT_ROOT / name
        if src.exists():
            _copy_tree(src, code_dir / name)

    for name in ARCHIVE_ROOT_FILES:
        src = PROJECT_ROOT / name
        if src.is_file():
            _copy_tree(src, code_dir / name)

    results_dir = dest / "results"
    results_dir.mkdir()
    if OUTPUTS_DIR.is_dir() and any(OUTPUTS_DIR.iterdir()):
        _copy_tree(OUTPUTS_DIR, results_dir / "outputs")

    for rel in extra_paths or []:
        src = rel if rel.is_absolute() else PROJECT_ROOT / rel
        if not src.exists():
            raise FileNotFoundError(f"extra path not found: {src}")
        if src.is_file():
            dst = results_dir / src.name
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            _copy_tree(src, results_dir / src.name)

    return dest


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive code and results to daima/YYYYMMDDHHMM"
    )
    parser.add_argument(
        "--stamp",
        help="Archive folder name (default: current time YYYYMMDDHHMM)",
    )
    parser.add_argument("--note", help="Optional note stored in archive_meta.txt")
    parser.add_argument(
        "--include",
        nargs="*",
        default=[],
        help="Extra files/dirs under project root to copy into results/",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing archive directory",
    )
    args = parser.parse_args()

    stamp = args.stamp or archive_stamp()
    dest = DAIMA_DIR / stamp
    if dest.exists():
        if not args.force:
            print(f"ERROR: archive already exists: {dest} (use --force to replace)")
            return 1
        shutil.rmtree(dest)

    extra = [Path(p) for p in args.include]
    path = create_archive(dest, extra_paths=extra, note=args.note)
    print(f"Archived to: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
