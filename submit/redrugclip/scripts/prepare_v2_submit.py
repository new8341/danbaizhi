#!/usr/bin/env python3
"""Package outputs/result_v2.csv into outputs/result_v2.zip (no root overwrite)."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import subprocess

from src.paths import OUTPUTS_DIR
from src.submission import package_result_zip


def main() -> int:
    csv_path = OUTPUTS_DIR / "result_v2.csv"
    log_path = OUTPUTS_DIR / "result.log"
    zip_path = OUTPUTS_DIR / "result_v2.zip"
    if not csv_path.is_file():
        print(f"Missing {csv_path}; run: py -3 scripts/run_inference.py --strategy hybrid_max_qed_v2 --output outputs/result_v2.csv")
        return 1

    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            f"\n[{datetime.now().isoformat()}] prepare_v2_submit: "
            f"packaging hybrid_max_qed_v2 -> {zip_path.name}\n"
        )

    package_result_zip(csv_path, log_path, zip_path, also_copy_to_root=False)
    print(f"Created {zip_path}")

    r = subprocess.run(
        [
            sys.executable,
            str(_ROOT / "scripts" / "validate_submission.py"),
            "--zip",
            str(zip_path),
        ],
        cwd=str(_ROOT),
    )
    return r.returncode


if __name__ == "__main__":
    raise SystemExit(main())
