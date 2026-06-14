"""Resolve competition data paths under /saisdata mounts."""
from __future__ import annotations

from pathlib import Path

from submit.pack_submission import emit_error


def first_existing(*candidates: Path) -> Path | None:
    for path in candidates:
        if path.exists():
            return path
    return None


def require_existing(label: str, *candidates: Path) -> Path:
    found = first_existing(*candidates)
    if found is None:
        emit_error(
            "SAISDATA_PATH_MISSING",
            f"{label} not found; tried: {', '.join(str(p) for p in candidates)}",
        )
    return found


def saisdata_subdir(saisdata: Path, *parts: str) -> Path:
    """Try /saisdata/<parts> then /saisdata/<mount_id>/<parts>."""
    if not parts:
        return saisdata
    joined = Path(*parts)
    candidates = [saisdata / joined]
    for mount_id in ("3", "37", "49", "48", "38", "36"):
        candidates.append(saisdata / mount_id / joined)
    found = first_existing(*candidates)
    return found if found is not None else saisdata / joined


def danbaizhi_data_root(saisdata: Path) -> Path:
    """Locate 1.json/2.json/3.json under flat or nested Tianchi mounts."""
    markers = ("1.json", "2.json", "3.json")

    def has_all_json(root: Path) -> bool:
        return all((root / name).is_file() for name in markers)

    if has_all_json(saisdata):
        return saisdata

    for mount_id in ("3", "38", "36", "48", "37", "49"):
        sub = saisdata / mount_id
        if has_all_json(sub):
            return sub

    if saisdata.is_dir():
        for child in sorted(saisdata.iterdir()):
            if child.is_dir() and has_all_json(child):
                return child

    return saisdata
