#!/usr/bin/env python
"""仓库维护：将代码与运行结果归档到 daima/YYYYMMDDHHMM。

非组织方复现路径（见 code/main.py）。在完整仓库布局下，spec 内路径相对仓库根目录。
"""

from __future__ import annotations

import argparse
import json
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class ArchiveSpec:
    """归档目录内的一项源路径及其目标相对名称。"""

    source: Path
    target_name: str


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _timestamp_folder_name() -> str:
    return datetime.now().strftime("%Y%m%d%H%M")


def _copy_path(src: Path, dst: Path) -> None:
    if src.is_dir():
        shutil.copytree(src, dst)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _copy_path_merge(src: Path, dst: Path) -> None:
    """同 _copy_path，但合并进已有目录（用于补充归档）。"""
    if src.is_dir():
        shutil.copytree(src, dst, dirs_exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)


def _build_default_specs(root: Path, run_dir: Path) -> list[ArchiveSpec]:
    """新建归档时默认复制的目录列表。"""
    specs = [
        ArchiveSpec(source=root / "scripts", target_name="scripts"),
        ArchiveSpec(source=root / "configs", target_name="configs"),
        ArchiveSpec(source=root / "document", target_name="document"),
        ArchiveSpec(source=root / "readme.md", target_name="readme.md"),
        ArchiveSpec(source=root / "tests", target_name="tests"),
        ArchiveSpec(source=root / "results" / "openmm", target_name="results/openmm"),
        ArchiveSpec(source=root / "results" / "submission", target_name="results/submission"),
        ArchiveSpec(source=root / "data" / "public", target_name="data/public"),
        ArchiveSpec(source=run_dir, target_name=f"extra_run_dir/{run_dir.name}"),
    ]
    existing = [s for s in specs if s.source.exists()]
    dedup: dict[str, ArchiveSpec] = {}
    for spec in existing:
        dedup.setdefault(str(spec.source.resolve()), spec)
    return list(dedup.values())


def _write_manifest(
    archive_dir: Path,
    copied: list[dict],
    note: str,
    *,
    supplement_log: list[dict] | None = None,
    created_at: str | None = None,
) -> None:
    """记录复制项及提交 zip 位置。"""
    submission_artifacts = []
    for item in copied:
        to_path = Path(item["to"])
        if to_path.name == "output.zip":
            submission_artifacts.append(str(to_path))
    submission_zip = archive_dir / "results" / "submission" / "output.zip"
    if submission_zip.exists():
        submission_artifacts.append(str(submission_zip))
    timeline_zip = archive_dir / "output.zip"
    if timeline_zip.exists():
        submission_artifacts.append(str(timeline_zip))
    payload: dict = {
        "created_at": created_at or datetime.now().isoformat(timespec="seconds"),
        "archive_dir": str(archive_dir),
        "note": note,
        "copied_items": copied,
        "submission_artifacts": sorted(set(submission_artifacts)),
        "timeline_output_zip": str(timeline_zip) if timeline_zip.exists() else "",
    }
    if supplement_log is not None:
        payload["supplement_log"] = supplement_log
    (archive_dir / "manifest.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# 新建归档目录
# ---------------------------------------------------------------------------
def archive_run(
    root: Path,
    run_dir: Path,
    daima_dir_name: str,
    timestamp: str | None,
    note: str,
    extra_paths: Iterable[Path],
) -> Path:
    daima_dir = root / daima_dir_name
    daima_dir.mkdir(parents=True, exist_ok=True)

    folder_name = timestamp.strip() if timestamp else _timestamp_folder_name()
    if len(folder_name) != 12 or not folder_name.isdigit():
        raise ValueError("Archive folder name must follow YYYYMMDDHHMM.")

    archive_dir = daima_dir / folder_name
    if archive_dir.exists():
        raise FileExistsError(
            f"Archive folder already exists: {archive_dir}. "
            "Use --timestamp with a different value."
        )
    archive_dir.mkdir(parents=True, exist_ok=False)

    copied: list[dict] = []
    for spec in _build_default_specs(root, run_dir):
        dst = archive_dir / spec.target_name
        _copy_path(spec.source, dst)
        copied.append({"from": str(spec.source), "to": str(dst)})

    for path in extra_paths:
        src = path if path.is_absolute() else (root / path)
        if not src.exists():
            raise FileNotFoundError(f"Extra path not found: {src}")
        dst = archive_dir / "extra" / src.name
        _copy_path(src, dst)
        copied.append({"from": str(src), "to": str(dst)})

    submission_zip_src = root / "results" / "submission" / "output.zip"
    if submission_zip_src.exists():
        dst_timeline = archive_dir / "output.zip"
        shutil.copy2(submission_zip_src, dst_timeline)
        copied.append(
            {"from": str(submission_zip_src), "to": str(dst_timeline), "role": "timeline_output_zip"}
        )

    _write_manifest(archive_dir, copied, note=note)
    return archive_dir


# ---------------------------------------------------------------------------
# 更新已有归档（--supplement）
# ---------------------------------------------------------------------------
def supplement_archive(
    root: Path,
    archive_dir: Path,
    note: str,
    extra_paths: Iterable[Path],
    *,
    refresh_submission: bool,
    refresh_timeline_zip: bool,
) -> Path:
    """向已有 daima/YYYYMMDDHHMM 追加路径并更新 manifest.json。"""
    ar = archive_dir if archive_dir.is_absolute() else (root / archive_dir)
    if not ar.is_dir():
        raise FileNotFoundError(f"Archive directory not found: {ar}")

    manifest_path = ar / "manifest.json"
    if manifest_path.exists():
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
        copied = list(payload.get("copied_items", []))
        base_note = str(payload.get("note", ""))
        supplement_log = list(payload.get("supplement_log", []))
        created_at = str(payload.get("created_at", ""))
    else:
        copied = []
        base_note = ""
        supplement_log = []
        created_at = datetime.now().isoformat(timespec="seconds")

    path_strs: list[str] = []
    for path in extra_paths:
        src = path if path.is_absolute() else (root / path)
        if not src.exists():
            raise FileNotFoundError(f"Extra path not found: {src}")
        dst = ar / "extra" / src.name
        _copy_path_merge(src, dst)
        rec = {"from": str(src), "to": str(dst), "role": "supplement"}
        copied.append(rec)
        path_strs.append(str(src))

    if refresh_submission:
        src = root / "results" / "submission"
        if not src.is_dir():
            raise FileNotFoundError(f"Cannot refresh: missing {src}")
        dst = ar / "results" / "submission"
        _copy_path_merge(src, dst)
        copied.append({"from": str(src), "to": str(dst), "role": "refresh_submission"})
        path_strs.append(str(src))

    if refresh_timeline_zip:
        submission_zip_src = root / "results" / "submission" / "output.zip"
        if not submission_zip_src.is_file():
            raise FileNotFoundError(f"Cannot refresh timeline zip: missing {submission_zip_src}")
        dst_timeline = ar / "output.zip"
        shutil.copy2(submission_zip_src, dst_timeline)
        copied.append(
            {
                "from": str(submission_zip_src),
                "to": str(dst_timeline),
                "role": "refresh_timeline_output_zip",
            }
        )
        path_strs.append(str(submission_zip_src))

    stamp = datetime.now().isoformat(timespec="seconds")
    supplement_log.append({"at": stamp, "note": note, "paths": path_strs})

    merged_note = base_note
    if note:
        merged_note = (
            f"{base_note} | supplement {stamp}: {note}".strip()
            if base_note
            else f"supplement {stamp}: {note}"
        )

    _write_manifest(
        ar,
        copied,
        note=merged_note,
        supplement_log=supplement_log,
        created_at=created_at or None,
    )
    return ar


# ---------------------------------------------------------------------------
# 命令行
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="归档代码与输出到 daima/YYYYMMDDHHMM"
    )
    parser.add_argument(
        "--run-dir",
        default="results/openmm",
        help="待归档的运行输出目录（默认 results/openmm）",
    )
    parser.add_argument(
        "--daima-dir",
        default="daima",
        help="归档根目录名（默认 daima）",
    )
    parser.add_argument(
        "--timestamp",
        default="",
        help="可选：归档文件夹名 YYYYMMDDHHMM",
    )
    parser.add_argument(
        "--note",
        default="",
        help="可选：写入 manifest.json 的备注",
    )
    parser.add_argument(
        "--extra-path",
        action="append",
        default=[],
        help="额外归档文件/目录（可多次指定）",
    )
    parser.add_argument(
        "--supplement",
        default="",
        help="已有归档目录（如 daima/202605100102）：将 --extra-path 合并到 extra/ "
        "and update manifest.json. Requires at least one --extra-path unless refresh flags are set.",
    )
    parser.add_argument(
        "--refresh-submission",
        action="store_true",
        help="配合 --supplement：合并当前 results/submission",
    )
    parser.add_argument(
        "--refresh-timeline-zip",
        action="store_true",
        help="配合 --supplement：将当前 output.zip 复制为归档根下 output.zip",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _project_root()
    supplement = (args.supplement or "").strip()

    if supplement:
        extra = [Path(p) for p in args.extra_path]
        if (
            not extra
            and not args.refresh_submission
            and not args.refresh_timeline_zip
        ):
            raise SystemExit(
                "[ERROR] --supplement requires --extra-path and/or --refresh-submission / "
                "--refresh-timeline-zip."
            )
        archive_dir = supplement_archive(
            root=root,
            archive_dir=Path(supplement),
            note=args.note.strip(),
            extra_paths=extra,
            refresh_submission=args.refresh_submission,
            refresh_timeline_zip=args.refresh_timeline_zip,
        )
        print(f"[DONE] Archive supplemented: {archive_dir}")
        print(f"[DONE] Manifest: {archive_dir / 'manifest.json'}")
        return

    run_dir = Path(args.run_dir)
    run_dir = run_dir if run_dir.is_absolute() else (root / run_dir)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    archive_dir = archive_run(
        root=root,
        run_dir=run_dir,
        daima_dir_name=args.daima_dir,
        timestamp=args.timestamp or None,
        note=args.note.strip(),
        extra_paths=[Path(p) for p in args.extra_path],
    )
    print(f"[DONE] Archive created: {archive_dir}")
    print(f"[DONE] Manifest: {archive_dir / 'manifest.json'}")


if __name__ == "__main__":
    main()
