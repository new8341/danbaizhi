"""DrugCLIP neural retrieval via external Uni-Mol stack (GPU)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from submit.tracks.drugclip_agent.benchmark import TaskInfo
from submit.tracks.drugclip_agent.lmdb import build_mol_lmdb_from_rows, build_pocket_lmdb
from submit.tracks.drugclip_agent.pocket import extract_task_pockets


def _drugclip_root() -> Path:
    return Path(os.environ.get("DRUGCLIP_ROOT", "/app/external/DrugCLIP"))


def _weights_dir() -> Path:
    return Path(os.environ.get("DRUGCLIP_WEIGHTS_DIR", "/app/weights"))


def drugclip_available() -> bool:
    root = _drugclip_root()
    retrieval = root / "unimol" / "retrieval.py"
    if not retrieval.is_file():
        return False
    weights = _weights_dir()
    return any(weights.glob("*.pt"))


def resolve_weights(task: TaskInfo) -> Path:
    weights = _weights_dir()
    if task.benchmark == "LIT-PCBA":
        path = weights / "litpcba_identity_90.pt"
        if path.is_file():
            return path
    dude = weights / "dude_identity_90.pt"
    if dude.is_file():
        return dude
    fallback = weights / "checkpoint_best.pt"
    if fallback.is_file():
        return fallback
    pts = sorted(weights.glob("*.pt"))
    if not pts:
        raise FileNotFoundError(f"No DrugCLIP weights in {weights}")
    return pts[0]


def run_drugclip_retrieval(
    mol_lmdb: Path,
    pocket_lmdb: Path,
    emb_dir: Path,
    weights: Path,
    *,
    batch_size: int | None = None,
    device: str | None = None,
) -> Path:
    root = _drugclip_root()
    emb_dir.mkdir(parents=True, exist_ok=True)
    batch_size = batch_size or int(os.environ.get("DRUGCLIP_BATCH_SIZE", "16"))
    device = device if device is not None else os.environ.get("DRUGCLIP_DEVICE", "0")

    cmd = [
        sys.executable,
        str(root / "unimol" / "retrieval.py"),
        "--user-dir",
        str(root / "unimol"),
        str(root / "data"),
        "--valid-subset",
        "test",
        "--results-path",
        str(emb_dir / "retrieval_out"),
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
    env = {**os.environ, "CUDA_VISIBLE_DEVICES": device}
    subprocess.run(cmd, cwd=str(root), check=True, env=env)
    return emb_dir / "ranked_compounds.txt"


def _parse_ranked(path: Path) -> dict[str, float]:
    scores: dict[str, float] = {}
    if not path.is_file():
        return scores
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or "\t" not in line:
            continue
        name, raw = line.split("\t", 1)
        try:
            scores[name.strip()] = float(raw.strip())
        except ValueError:
            continue
    return scores


def score_task_neural(
    task: TaskInfo,
    ligand_rows: list[dict[str, str]],
    work_root: Path,
) -> tuple[dict[str, float], list[str]]:
    """Run DrugCLIP retrieval for one task; return ligand_id → score."""
    logs: list[str] = []
    task_dir = work_root / task.task_id
    task_dir.mkdir(parents=True, exist_ok=True)
    mol_lmdb = task_dir / "mols.lmdb"
    pocket_lmdb = task_dir / "pocket.lmdb"
    emb_dir = task_dir / "emb"

    logs.append(f"[agent] neural_phase=lmdb_mol task={task.task_id} ligands={len(ligand_rows)}")
    n_mol = build_mol_lmdb_from_rows(ligand_rows, mol_lmdb)
    logs.append(f"[agent] neural_phase=lmdb_mol_done records={n_mol}")

    pockets = extract_task_pockets(task)
    logs.append(f"[agent] neural_phase=lmdb_pocket pockets={len(pockets)}")
    n_poc = build_pocket_lmdb(pockets, pocket_lmdb)
    logs.append(f"[agent] neural_phase=lmdb_pocket_done records={n_poc}")

    weights = resolve_weights(task)
    logs.append(f"[agent] neural_phase=retrieve weights={weights.name}")
    ranked = run_drugclip_retrieval(mol_lmdb, pocket_lmdb, emb_dir, weights)
    raw_scores = _parse_ranked(ranked)
    logs.append(f"[agent] neural_phase=retrieve_done ranked={len(raw_scores)}")

    scores: dict[str, float] = {}
    for row in ligand_rows:
        lid = row["ligand_id"]
        scores[lid] = raw_scores.get(lid, 0.0)
    return scores, logs


def blend_neural_hybrid(
    neural: dict[str, float],
    hybrid: dict[str, float],
    neural_weight: float,
) -> dict[str, float]:
    """Min-max normalize each dict then linear blend."""
    if not neural:
        return hybrid
    if not hybrid:
        return neural

    def _norm(d: dict[str, float]) -> dict[str, float]:
        vals = list(d.values())
        lo, hi = min(vals), max(vals)
        span = hi - lo if hi > lo else 1.0
        return {k: (v - lo) / span for k, v in d.items()}

    nn = _norm(neural)
    hn = _norm(hybrid)
    alpha = max(0.0, min(1.0, neural_weight))
    keys = set(nn) | set(hn)
    return {k: alpha * nn.get(k, 0.0) + (1.0 - alpha) * hn.get(k, 0.0) for k in keys}
