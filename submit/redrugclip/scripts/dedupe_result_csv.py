#!/usr/bin/env python3
"""Remove duplicate (task_id, ligand_id) rows, keep highest score."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from src.paths import OUTPUTS_DIR


def main() -> int:
    src = OUTPUTS_DIR / "result.csv"
    dst = OUTPUTS_DIR / "result_deduped.csv"
    best: dict[tuple[str, str], float] = {}
    with src.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            key = (row["task_id"], row["ligand_id"])
            score = float(row["score"])
            if key not in best or score > best[key]:
                best[key] = score
    with dst.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "ligand_id", "score"])
        for (tid, lid), score in sorted(best.items()):
            w.writerow([tid, lid, f"{score:.6f}"])
    print(f"unique={len(best)} wrote {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
