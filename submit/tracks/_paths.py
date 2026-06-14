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


def describe_saisdata(saisdata: Path, max_depth: int = 3, max_lines: int = 80) -> str:
    """Summarize /saisdata layout for Tianchi diagnostics."""
    if not saisdata.exists():
        return f"{saisdata} does not exist"
    if not saisdata.is_dir():
        return f"{saisdata} is not a directory"

    lines: list[str] = []
    root_entries = sorted(saisdata.iterdir(), key=lambda p: p.name)
    lines.append(f"top={ [p.name + ('/' if p.is_dir() else '') for p in root_entries] }")

    count = 0
    for path in sorted(saisdata.rglob("*")):
        if count >= max_lines:
            lines.append("...(truncated)")
            break
        rel = path.relative_to(saisdata)
        if 1 <= len(rel.parts) <= max_depth:
            suffix = "/" if path.is_dir() else ""
            lines.append(f"  {rel.as_posix()}{suffix}")
            count += 1
    return "; ".join(lines)


def danbaizhi_data_root(saisdata: Path) -> Path:
    """Locate 1.json/2.json/3.json under flat or nested Tianchi mounts."""
    markers = ("1.json", "2.json", "3.json")

    def has_all_json(root: Path) -> bool:
        return all((root / name).is_file() for name in markers)

    if has_all_json(saisdata):
        return saisdata

    for mount_id in ("3", "36", "38", "37", "48", "49"):
        sub = saisdata / mount_id
        if has_all_json(sub):
            return sub

    if saisdata.is_dir():
        for child in sorted(saisdata.iterdir()):
            if child.is_dir() and has_all_json(child):
                return child

        queue: list[tuple[Path, int]] = [(saisdata, 0)]
        while queue:
            current, depth = queue.pop(0)
            if depth > 0 and has_all_json(current):
                return current
            if depth >= 4:
                continue
            try:
                for child in sorted(current.iterdir()):
                    if child.is_dir():
                        queue.append((child, depth + 1))
            except OSError:
                continue

    return saisdata
