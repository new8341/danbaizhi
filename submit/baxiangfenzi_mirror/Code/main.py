#!/usr/bin/env python3
"""Baxiangfenzi 复赛代码审核入口（推理说明）。

正式评测入口：/app/run.sh → submit/main.py --track baxiangfenzi
本文件供组委会审阅 Agent 推理链路，不替代 Docker 入口。
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    print("=== Baxiangfenzi Agent (semifinal code review) ===")
    print("Docker entry : /app/run.sh")
    print("Track runner : submit/tracks/baxiangfenzi_agent/pipeline.py")
    print("Input mount  : /saisdata/37/target{1,2,3}.pdb  (B榜同名同路径)")
    print("Output       : /saisresult/result.zip")
    print("LLM API key  : env BAXIANG_LLM_API_KEY (see Code/README.md)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
