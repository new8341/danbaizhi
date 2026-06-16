#!/usr/bin/env python3
"""Run score-informed optimization: pilot search then full inference + submit."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from agent.runner import DrugClipAgent


def main() -> int:
    agent = DrugClipAgent()
    agent.log.header("Score-informed optimization (platform feedback)")
    agent.log.line("2026-05-21 hybrid_max_qed → 18.873261")
    agent.log.line("2026-05-22 ensemble_ef1_sharp → 11.294361 (reverted)")
    agent.log.flush()
    zip_path = agent.run(skip_archive=False)
    if zip_path:
        print(f"Done: {zip_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
