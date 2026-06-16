#!/usr/bin/env python3
"""RRF fuse champion (18.87) + v2; package to outputs/result_fusion.zip."""

from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.fusion import load_scores, reciprocal_rank_fusion, write_fused_csv
from src.paths import OUTPUTS_DIR, PROJECT_ROOT
from src.submission import package_result_zip


def main() -> int:
    champ = PROJECT_ROOT / "daima" / "202605212027" / "results" / "result.csv"
    v2 = OUTPUTS_DIR / "result_v2.csv"
    if not champ.is_file():
        print(f"Missing {champ}")
        return 1
    if not v2.is_file():
        print(f"Missing {v2}")
        return 1

    fused = reciprocal_rank_fusion(
        [load_scores(champ), load_scores(v2)],
        weights=[0.85, 0.15],
        k=60,
    )
    csv_path = OUTPUTS_DIR / "result_fusion.csv"
    write_fused_csv(fused, csv_path)
    log_path = OUTPUTS_DIR / "result.log"
    with log_path.open("a", encoding="utf-8") as f:
        f.write(
            f"\n[{datetime.now().isoformat()}] RRF fusion champion(0.85)+v2(0.15) "
            f"rows={len(fused)}\n"
        )
    zip_path = OUTPUTS_DIR / "result_fusion.zip"
    package_result_zip(csv_path, log_path, zip_path)
    print(f"Created {zip_path} ({len(fused)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
