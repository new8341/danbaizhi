#!/usr/bin/env python
"""Project 入口（tijiao.md）。

子进程的工作目录均为 Project 根目录；命令行路径相对该根目录
（如 data/、processed_data/、checkpoint/、result/）。

子命令：
  （默认）/ predict  — 生成 result/output.zip（组织方复现）
  eval               — 本地弱评测
  build-prior        — 可选：离线合并 ColabFold 先验配置
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# 路径：Project 根目录为本文件所在目录（code/）的上一级
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CODE = PROJECT_ROOT / "code"


def _run(cmd: list[str]) -> None:
    """在 PROJECT_ROOT 下启动子脚本，使相对路径可正确解析。"""
    print("[CMD]", " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=str(PROJECT_ROOT), check=True)


# ---------------------------------------------------------------------------
# predict：主预测流程（组织方需执行）
# ---------------------------------------------------------------------------
def cmd_predict(_args: argparse.Namespace) -> None:
    """调用 generate_submission.py，使用冻结配置与 seed=42。"""
    import os

    cfg = PROJECT_ROOT / "processed_data" / "configs" / "submission_sources.json"
    if os.environ.get("DANBAIZHI_AUTO_PRIOR", "1").strip().lower() not in {"0", "false", "no"}:
        sys.path.insert(0, str(CODE))
        from build_sequence_prior_sources import resolve_runtime_sources_config

        cfg = resolve_runtime_sources_config(PROJECT_ROOT)
        print(f"[Danbaizhi] sources_config={cfg.relative_to(PROJECT_ROOT)}", flush=True)
    _run(
        [
            sys.executable,
            str(CODE / "generate_submission.py"),
            "--problems-dir",
            "data",
            "--out-dir",
            "result",
            "--zip-name",
            "output.zip",
            "--sources-config",
            str(cfg.relative_to(PROJECT_ROOT)).replace("\\", "/"),
            "--seed",
            "42",
        ]
    )


# ---------------------------------------------------------------------------
# eval：可选的几何/多样性检查（不改变提交内容）
# ---------------------------------------------------------------------------
def cmd_eval(_args: argparse.Namespace) -> None:
    """对 result/output.zip 运行 eval_submission_local.py。"""
    _run(
        [
            sys.executable,
            str(CODE / "eval_submission_local.py"),
            "--zip",
            "result/output.zip",
            "--problems-dir",
            "data",
            "--out-json",
            "result/local_eval.json",
        ]
    )


# ---------------------------------------------------------------------------
# build-prior：离线将 ColabFold 输出合并进 sources JSON（可选）
# ---------------------------------------------------------------------------
def cmd_build_prior(_args: argparse.Namespace) -> None:
    """扫描 processed_data/colabfold，写出 submission_sources_merged.json。"""
    _run(
        [
            sys.executable,
            str(CODE / "build_sequence_prior_sources.py"),
            "--base-config",
            "processed_data/configs/submission_sources.json",
            "--candidate-root",
            "processed_data/colabfold",
            "--out-config",
            "processed_data/configs/submission_sources_merged.json",
            "--prefer-sequence-prior",
            "--min-mean-plddt",
            "50",
        ]
    )


# ---------------------------------------------------------------------------
# CLI：未指定子命令时默认执行 predict
# ---------------------------------------------------------------------------
def main() -> int:
    p = argparse.ArgumentParser(description="蛋白质构象系综 Project（代码审核）")
    sub = p.add_subparsers(dest="command")
    sub.add_parser("predict", help="生成 result/output.zip（默认）").set_defaults(func=cmd_predict)
    sub.add_parser("eval", help="本地评测 result/output.zip").set_defaults(func=cmd_eval)
    sub.add_parser("build-prior", help="重建序列先验配置").set_defaults(func=cmd_build_prior)
    args = p.parse_args()
    if args.command is None:
        cmd_predict(args)
    else:
        args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
