#!/usr/bin/env python3
"""Pack staged files into /saisresult/submission.zip (or track-specific name).

/saisresult does not support seek; always build under /app first, then mv.
"""
from __future__ import annotations

import json
import shutil
import sys
import uuid
import zipfile
from pathlib import Path


def error_payload(code: str, message: str, request_id: str | None = None) -> dict:
    return {
        "success": False,
        "error": {
            "code": code,
            "message": message,
            "requestId": request_id or str(uuid.uuid4()),
        },
    }


def emit_error(code: str, message: str, request_id: str | None = None, exit_code: int = 1) -> None:
    print(json.dumps(error_payload(code, message, request_id), ensure_ascii=False), flush=True)
    raise SystemExit(exit_code)


def pack_directory(staging_dir: Path, zip_path: Path) -> None:
    """Create zip from directory contents (not the directory itself)."""
    staging_dir = staging_dir.resolve()
    if not staging_dir.is_dir():
        emit_error("PACK_STAGING_MISSING", f"Staging directory not found: {staging_dir}")

    zip_path.parent.mkdir(parents=True, exist_ok=True)
    build_path = zip_path.with_suffix(".zip.build")
    if build_path.exists():
        build_path.unlink()

    with zipfile.ZipFile(build_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in sorted(staging_dir.rglob("*")):
            if item.is_file():
                zf.write(item, item.relative_to(staging_dir).as_posix())

    if zip_path.exists():
        zip_path.unlink()
    shutil.move(str(build_path), str(zip_path))


def copy_zip(src: Path, dest: Path) -> None:
    if not src.is_file():
        emit_error("PACK_SOURCE_MISSING", f"Source zip not found: {src}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)


def move_to_saisresult(local_zip: Path, saisresult_path: Path) -> None:
    saisresult_path.parent.mkdir(parents=True, exist_ok=True)
    if saisresult_path.exists():
        saisresult_path.unlink()
    shutil.move(str(local_zip), str(saisresult_path))
