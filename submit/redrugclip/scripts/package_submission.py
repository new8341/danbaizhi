#!/usr/bin/env python3
"""Package outputs/result.csv + result.log into result.zip and validate."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
import subprocess

from src.paths import OUTPUTS_DIR
from src.submission import package_result_zip


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", default=str(OUTPUTS_DIR / "result.csv"))
    parser.add_argument("--log", default=str(OUTPUTS_DIR / "result.log"))
    parser.add_argument("--zip", default=str(OUTPUTS_DIR / "result.zip"))
    args = parser.parse_args()

    zip_path = package_result_zip(Path(args.csv), Path(args.log), Path(args.zip))
    print(f"Created {zip_path}")

    r = subprocess.run(
        [sys.executable, str(_ROOT / "scripts" / "validate_submission.py"), "--zip", str(zip_path)],
        cwd=str(_ROOT),
    )
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
