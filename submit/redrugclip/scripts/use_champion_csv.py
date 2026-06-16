#!/usr/bin/env python3
"""Restore platform 18.87 champion CSV from daima archive."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
CHAMPION = _ROOT / "daima" / "202605212027" / "results" / "result.csv"
OUT = _ROOT / "outputs" / "result.csv"


def main() -> int:
    if not CHAMPION.is_file():
        print(f"Missing champion archive: {CHAMPION}")
        return 1
    shutil.copy2(CHAMPION, OUT)
    print(f"Restored {OUT} from champion (platform score 18.873261)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
