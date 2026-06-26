#!/usr/bin/env python3
"""离线训练辅助：在 Windows 上通过 WSL 运行 LocalColabFold 的 colabfold_batch。

由 run_colabfold_optional.py 在 COLABFOLD_WSL=1 时调用；FASTA/输出路径经 wslpath 转换。
建议尽量使用 Project/ 下的相对路径。

可选环境变量：
  COLABFOLD_WSL_DISTRO   WSL 发行版名（默认 Ubuntu-22.04）
  COLABFOLD_WSL_BIN      colabfold_batch 的 Linux 完整路径
  COLABFOLD_WSL_CPU      在 WSL 内强制 JAX_PLATFORMS=cpu
  COLABFOLD_WSL_XDG_CACHE  Windows 目录映射为 WSL 内 XDG_CACHE_HOME
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------
def _repo_root() -> Path:
    """Project 根目录（code/ 的上一级）。"""
    return Path(__file__).resolve().parents[1]


def _default_colabfold_bin_wsl(root_wsl: str) -> str:
    """localcolabfold-main/.pixi 下 colabfold_batch 的默认 Linux 路径。"""
    base = root_wsl.rstrip("/")
    return f"{base}/localcolabfold-main/.pixi/envs/default/bin/colabfold_batch"


def _win_path_for_wslpath_cli(windows_path: str) -> str:
    """wslpath 前将 Windows 路径规范为正斜杠，避免反斜杠丢失。"""
    p = Path(windows_path).resolve()
    s = str(p)
    if len(s) >= 2 and s[1] == ":":
        return s.replace("\\", "/")
    return s


def _truthy_env(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in ("1", "true", "yes", "on")


def wslpath_u(windows_path: str, *, distro: str) -> str:
    """通过 wsl wslpath -a 将 Windows 路径转为 WSL 绝对路径。"""
    arg = _win_path_for_wslpath_cli(windows_path)
    r = subprocess.run(
        ["wsl", "-d", distro, "wslpath", "-a", arg],
        capture_output=True,
        text=True,
        check=False,
    )
    if r.returncode != 0:
        msg = (r.stderr or r.stdout or "").strip()
        raise RuntimeError(
            f"wslpath failed (exit {r.returncode}) for {windows_path!r}: {msg}\n"
            f"  Distro: {distro!r}. Check: wsl -l -v"
        )
    return r.stdout.strip()


# ---------------------------------------------------------------------------
# 主流程：组装 bash 命令并在 WSL 中执行 colabfold_batch
# ---------------------------------------------------------------------------
def main() -> int:
    distro = os.environ.get("COLABFOLD_WSL_DISTRO", "Ubuntu-22.04").strip() or "Ubuntu-22.04"
    root = _repo_root()
    root_wsl = wslpath_u(str(root), distro=distro)
    raw_bin = os.environ.get("COLABFOLD_WSL_BIN", "").strip()
    cf_bin = raw_bin or _default_colabfold_bin_wsl(root_wsl)

    if len(sys.argv) < 3:
        print(
            "colabfold_batch_wsl: need at least <fasta> <outdir> [extra args...]\n"
            "Set COLABFOLD_BATCH to scripts/colabfold_batch_wsl.cmd or run via run_colabfold_optional.",
            file=sys.stderr,
        )
        return 2

    # argv[1]=FASTA，argv[2]=输出目录，argv[3:]=colabfold_batch 额外参数
    p_fast = wslpath_u(sys.argv[1], distro=distro)
    p_out = wslpath_u(sys.argv[2], distro=distro)
    rest = [str(a) for a in sys.argv[3:]]

    # WSL 内可选环境（pixi PATH、缓存目录、CPU 回退）
    exports: list[str] = ['export PATH="${HOME}/.pixi/bin:$PATH"']
    cache_win = os.environ.get("COLABFOLD_WSL_XDG_CACHE", "").strip()
    if cache_win:
        Path(cache_win).expanduser().resolve().mkdir(parents=True, exist_ok=True)
        cache_wsl = wslpath_u(cache_win, distro=distro)
        exports.append(f"export XDG_CACHE_HOME={shlex.quote(cache_wsl)}")
    if _truthy_env("COLABFOLD_WSL_CPU"):
        exports.append("export JAX_PLATFORMS=cpu")

    inner_parts = [cf_bin, p_fast, p_out, *rest]
    inner = " ".join(shlex.quote(p) for p in inner_parts)
    bash = " && ".join(exports) + f" && exec {inner}"

    cmd = ["wsl", "-d", distro, "--", "bash", "-lc", bash]
    r = subprocess.run(cmd)
    return int(r.returncode)


if __name__ == "__main__":
    raise SystemExit(main())
