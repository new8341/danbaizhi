"""Optional DrugCLIP retrieval via external/bowen-gao/DrugCLIP (GPU recommended)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from src.paths import PROJECT_ROOT

DRUGCLIP_ROOT = PROJECT_ROOT / "external" / "DrugCLIP"
DEFAULT_WEIGHTS = PROJECT_ROOT / "weights" / "checkpoint_best.pt"


def drugclip_available() -> bool:
    retrieval = DRUGCLIP_ROOT / "unimol" / "retrieval.py"
    return retrieval.is_file() and DEFAULT_WEIGHTS.is_file()


def run_drugclip_retrieval(
    mol_lmdb: Path,
    pocket_lmdb: Path,
    emb_dir: Path,
    weights: Path | None = None,
    batch_size: int = 8,
    device: str = "0",
) -> Path:
    weights = weights or DEFAULT_WEIGHTS
    emb_dir.mkdir(parents=True, exist_ok=True)
    results_path = emb_dir / "retrieval_out"
    results_path.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(DRUGCLIP_ROOT / "unimol" / "retrieval.py"),
        "--user-dir",
        str(DRUGCLIP_ROOT / "unimol"),
        str(DRUGCLIP_ROOT / "data"),
        "--valid-subset",
        "test",
        "--results-path",
        str(results_path),
        "--num-workers",
        "4",
        "--batch-size",
        str(batch_size),
        "--task",
        "drugclip",
        "--loss",
        "in_batch_softmax",
        "--arch",
        "drugclip",
        "--max-pocket-atoms",
        "256",
        "--seed",
        "1",
        "--path",
        str(weights),
        "--log-interval",
        "100",
        "--log-format",
        "simple",
        "--mol-path",
        str(mol_lmdb),
        "--pocket-path",
        str(pocket_lmdb),
        "--emb-dir",
        str(emb_dir),
    ]
    env = {"CUDA_VISIBLE_DEVICES": device}
    subprocess.run(cmd, cwd=str(DRUGCLIP_ROOT), check=True, env={**os.environ, **env})
    ranked = emb_dir / "ranked_compounds.txt"
    return ranked
