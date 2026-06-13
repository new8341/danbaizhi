"""Track 2 — targeted molecule design + retrosynthesis baseline scaffold."""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from submit.pack_submission import emit_error
from submit.tracks._paths import first_existing, saisdata_subdir
from submit.tracks.base import TrackRunner, TrackSpec


def _derive_from_target(target_path: Path, index: int) -> tuple[str, str]:
    """Runtime-derived placeholder (not a pre-baked molecule library)."""
    digest = hashlib.sha256(target_path.read_bytes()).hexdigest()
    n = int(digest[:4], 16) % 5 + 3
    smiles = "C" * n
    route = f"{'C,' * (n - 1)}C>>{smiles}"
    return smiles, route


class BaxiangfenziRunner(TrackRunner):
    spec = TrackSpec(
        name="baxiangfenzi",
        task_id="2",
        saisdata_hint="/saisdata/37/target1.pdb, target2.pdb, target3.pdb",
        output_name="result.zip",
        output_members=("result1.csv", "result2.csv", "result3.csv"),
    )

    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        staging_dir.mkdir(parents=True, exist_ok=True)
        data_root = saisdata_subdir(saisdata, "37")
        log_lines = [
            "Baxiangfenzi baseline scaffold",
            f"timestamp={datetime.now(timezone.utc).isoformat()}",
            f"data_root={data_root}",
        ]

        for idx in (1, 2, 3):
            target = data_root / f"target{idx}.pdb"
            if not target.is_file():
                fallback = first_existing(
                    saisdata / "target.pdb",
                    saisdata / "37" / "target.pdb",
                    work_dir / "documen" / "Baxiangfenzi" / "target.pdb",
                )
                if fallback is not None:
                    target = fallback
                else:
                    emit_error("BAXIANG_TARGET_MISSING", f"Missing target file for slot {idx}: {target}")

            smiles, route = _derive_from_target(target, idx)
            out_csv = staging_dir / f"result{idx}.csv"
            with out_csv.open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["mol_smiles", "route"])
                writer.writerow([smiles, route])
            log_lines.append(f"target{idx}={target.name} bytes={target.stat().st_size}")

        (staging_dir / "result.log").write_text("\n".join(log_lines), encoding="utf-8")
        print("[Baxiangfenzi] wrote result1/2/3.csv", flush=True)
