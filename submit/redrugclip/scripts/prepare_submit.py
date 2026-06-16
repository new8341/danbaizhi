#!/usr/bin/env python3
"""
Prepare competition submission per document/rull.md:
  - Filename: result.zip (upload name: result)
  - Contents: result.csv + result.log only
  - Size limit: <= 100 MB
Then archive to daima/YYYYMMDDHHMM.
"""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import argparse
import subprocess

from src.paths import OUTPUTS_DIR, PROJECT_ROOT
from src.submission import (
    MAX_ZIP_BYTES,
    SUBMIT_CSV_NAME,
    SUBMIT_LOG_NAME,
    SUBMIT_ZIP_NAME,
    package_result_zip,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Package result.zip and archive")
    parser.add_argument("--csv", default=str(OUTPUTS_DIR / SUBMIT_CSV_NAME))
    parser.add_argument("--log", default=str(OUTPUTS_DIR / SUBMIT_LOG_NAME))
    parser.add_argument("--no-archive", action="store_true")
    parser.add_argument("--skip-validate", action="store_true")
    args = parser.parse_args()

    csv_path = Path(args.csv)
    log_path = Path(args.log)

    zip_path = package_result_zip(csv_path, log_path, also_copy_to_root=True)
    root_zip = PROJECT_ROOT / SUBMIT_ZIP_NAME
    size_mb = zip_path.stat().st_size / 1024 / 1024

    print(f"Created: {zip_path}")
    print(f"Upload:  {root_zip}  ({size_mb:.2f} MB / {MAX_ZIP_BYTES // 1024 // 1024} MB max)")
    print(f"Contains: {SUBMIT_CSV_NAME}, {SUBMIT_LOG_NAME}")

    if not args.skip_validate:
        r = subprocess.run(
            [
                sys.executable,
                str(_ROOT / "scripts" / "validate_submission.py"),
                "--zip",
                str(zip_path),
            ],
            cwd=str(_ROOT),
        )
        if r.returncode != 0:
            return r.returncode

    if not args.no_archive:
        stamp = datetime.now().strftime("%Y%m%d%H%M")
        note = "submission result.zip packaged per rull.md"
        subprocess.run(
            [
                sys.executable,
                str(_ROOT / "scripts" / "archive_run.py"),
                "--stamp",
                stamp,
                "--note",
                note,
                "--include",
                f"outputs/{SUBMIT_CSV_NAME}",
                f"outputs/{SUBMIT_LOG_NAME}",
                f"outputs/{SUBMIT_ZIP_NAME}",
                SUBMIT_ZIP_NAME,
            ],
            cwd=str(_ROOT),
            check=True,
        )
        print(f"Archived: daima/{stamp}/")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
