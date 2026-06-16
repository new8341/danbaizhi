#!/usr/bin/env python3
"""Restore platform 18.87 champion, package, archive."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import subprocess


def main() -> int:
    subprocess.run([sys.executable, str(_ROOT / "scripts" / "use_champion_csv.py")], check=True)
    log = _ROOT / "outputs" / "result.log"
    with log.open("a", encoding="utf-8") as f:
        f.write(
            f"\n[{datetime.now().isoformat()}] Restored champion hybrid_max_qed "
            f"(platform 18.873261) as primary submission.\n"
        )
    subprocess.run([sys.executable, str(_ROOT / "scripts" / "prepare_submit.py")], check=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M")
    subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "archive_run.py"),
            "--stamp",
            stamp,
            "--note",
            "champion 18.87 primary",
            "--force",
            "--include",
            "outputs/result.csv",
            "outputs/result.log",
            "outputs/result.zip",
            "result.zip",
        ],
        cwd=str(_ROOT),
        check=True,
    )
    print(f"Champion ready: {_ROOT / 'result.zip'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
