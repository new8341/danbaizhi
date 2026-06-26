#!/usr/bin/env python
"""可选离线训练：ColabFold / localcolabfold 批量预测（序列 -> PDB/mmCIF）。

不由 code/main.py predict 调用；输出写在 --out-root（如 processed_data/colabfold）。
若未找到 colabfold_batch，以退出码 0 打印 [SKIP]，便于流水线无条件调用。
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Project 根目录与 ColabFold 可执行文件定位
# ---------------------------------------------------------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _wsl_flag(name: str) -> bool:
    v = os.environ.get(name, "").strip().lower()
    return v in ("1", "true", "yes", "on")


def _find_batch() -> str | None:
    """解析 colabfold_batch：环境变量 COLABFOLD_BATCH、PATH，或 Windows 下 WSL 包装脚本。"""
    env = os.environ.get("COLABFOLD_BATCH", "").strip()
    if env and Path(env).is_file():
        return env
    found = shutil.which("colabfold_batch")
    if found:
        return found
    if platform.system() == "Windows" and _wsl_flag("COLABFOLD_WSL"):
        wsl_cmd = _project_root() / "scripts" / "colabfold_batch_wsl.cmd"
        if wsl_cmd.is_file():
            return str(wsl_cmd)
    return None


def _read_sequence(problems_dir: Path, problem_id: int) -> str:
    """从 data/{id}.json 读取目标序列。"""
    path = problems_dir / f"{problem_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    return data[0]["sequences"][0]["proteinChain"]["sequence"].strip()


# ---------------------------------------------------------------------------
# 命令行
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="可选：对赛题序列批量运行 ColabFold")
    p.add_argument("--problems-dir", default="document", help="含 1.json 2.json 3.json 的目录")
    p.add_argument(
        "--out-root",
        default="results/colabfold",
        help="输出根目录；每题一个 problem_{id} 子目录",
    )
    p.add_argument("--models", type=int, default=3, help="传给 colabfold_batch 的 --num-models")
    p.add_argument("--recycles", type=int, default=1, help="传给 colabfold_batch 的 --num-recycle")
    p.add_argument("--dry-run", action="store_true", help="仅打印将要执行的命令")
    p.add_argument(
        "--batch-arg",
        action="append",
        default=[],
        metavar="ARG",
        help="colabfold_batch 额外参数（每个 token 重复一次本标志）",
    )
    p.add_argument(
        "--only-problem",
        type=int,
        choices=[1, 2, 3],
        action="append",
        dest="only_problems",
        default=None,
        metavar="N",
        help="仅运行第 N 题（可重复）。默认 1 2 3",
    )
    p.add_argument(
        "--fast-preview",
        action="store_true",
        help="快速预览：1 模型、1 recycle、single_sequence MSA",
    )
    p.add_argument(
        "--predictions-subdir",
        default="predictions",
        help="problem_{id}/ 下输出子目录（如 predictions_msa）",
    )
    return p.parse_args()


# ---------------------------------------------------------------------------
# 主循环：每题一个 FASTA + 输出目录
# ---------------------------------------------------------------------------
def main() -> int:
    args = parse_args()
    root = _project_root()
    batch = _find_batch()
    if not batch:
        print(
            "[SKIP] colabfold_batch not found. Install LocalColabFold, set COLABFOLD_BATCH, "
            "or on Windows with WSL: set COLABFOLD_WSL=1 and use scripts/colabfold_batch_wsl.cmd.\n"
            "  See: https://github.com/YoshitakaMo/localcolabfold",
            file=sys.stderr,
        )
        return 0

    if args.fast_preview:
        print(
            "[INFO] --fast-preview: num-models=1, num-recycle=1, --msa-mode single_sequence",
            flush=True,
        )

    # 相对路径均相对 Project 根目录解析
    problems_dir = Path(args.problems_dir)
    problems_dir = problems_dir if problems_dir.is_absolute() else (root / problems_dir)
    out_root = Path(args.out_root)
    out_root = out_root if out_root.is_absolute() else (root / out_root)
    out_root.mkdir(parents=True, exist_ok=True)

    models = 1 if args.fast_preview else args.models
    recycles = 1 if args.fast_preview else args.recycles
    batch_tail: list[str] = []
    if args.fast_preview:
        batch_tail.extend(["--msa-mode", "single_sequence"])
    batch_tail.extend(str(a) for a in args.batch_arg)

    pids = sorted(set(args.only_problems)) if args.only_problems else [1, 2, 3]
    for pid in pids:
        seq = _read_sequence(problems_dir, pid)
        job = out_root / f"problem_{pid}"
        job.mkdir(parents=True, exist_ok=True)
        fasta = job / f"p{pid}.fasta"
        fasta.write_text(f">p{pid}\n{seq}\n", encoding="utf-8")
        pred_dir = job / str(args.predictions_subdir).strip("/\\")
        pred_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            batch,
            str(fasta),
            str(pred_dir),
            "--num-models",
            str(models),
            "--num-recycle",
            str(recycles),
        ]
        cmd.extend(batch_tail)

        print(f"[CMD] {' '.join(cmd)}", flush=True)
        if pred_dir.exists() and any(pred_dir.iterdir()):
            print(
                f"[INFO] Reusing output dir {pred_dir} (MSA/checkpoints may skip re-download)",
                flush=True,
            )
        if args.dry_run:
            continue
        r = subprocess.run(cmd, cwd=str(root))
        if r.returncode != 0:
            print(
                f"[WARN] colabfold_batch failed for problem {pid} (exit {r.returncode})",
                file=sys.stderr,
                flush=True,
            )

    print(f"[DONE] ColabFold outputs under {out_root}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
