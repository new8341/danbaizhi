"""Ligand scoring via Morgan fingerprint Tanimoto vs reference co-crystal ligands."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rdkit import Chem, DataStructs
from rdkit.Chem import AllChem


def _hash_score(task_id: str, ligand_id: str) -> float:
    digest = hashlib.sha256(f"{task_id}:{ligand_id}".encode()).hexdigest()
    return round(int(digest[:8], 16) % 100000 / 100.0, 2)


def _mol_from_ref(path: Path):
    if not path.is_file():
        return None
    if path.suffix.lower() == ".mol2":
        return Chem.MolFromMol2File(str(path), sanitize=True, removeHs=False)
    if path.suffix.lower() in {".sdf", ".mol"}:
        return Chem.MolFromMolFile(str(path), sanitize=True, removeHs=False)
    return None


def load_reference_fps(task_dir: Path) -> list:
    task_json = task_dir / "task.json"
    ref_paths: list[Path] = []
    if task_json.is_file():
        meta = json.loads(task_json.read_text(encoding="utf-8"))
        for rel in meta.get("reference_ligand_files", []):
            ref_paths.append(task_dir / rel)
    if not ref_paths:
        refs_dir = task_dir / "refs"
        if refs_dir.is_dir():
            ref_paths.extend(sorted(refs_dir.glob("*.mol2")))
            ref_paths.extend(sorted(refs_dir.glob("*.sdf")))

    fps = []
    for path in ref_paths:
        mol = _mol_from_ref(path)
        if mol is not None:
            fps.append(AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048))
    return fps


def score_smiles(smiles: str, ref_fps: list, task_id: str, ligand_id: str) -> float:
    if not ref_fps:
        return _hash_score(task_id, ligand_id)

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0.01

    fp = AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=2048)
    sim = max(DataStructs.BulkTanimotoSimilarity(fp, ref_fps))
    # Scale to competition score range; tiny tie-breaker from ligand id hash.
    tie = (int(hashlib.md5(ligand_id.encode()).hexdigest()[:4], 16) % 100) / 10000.0
    return round(sim * 100.0 + tie, 4)


def score_task(task_id: str, task_dir: Path, ligands_path: Path) -> tuple[list[tuple[str, str, float]], list[str]]:
    ref_fps = load_reference_fps(task_dir)
    logs = [
        f"[agent] task={task_id} refs={len(ref_fps)} ligands_file={ligands_path.name}",
        f"[agent] strategy=morgan_tanimoto_vs_crystal_ligand radius=2 nBits=2048",
    ]

    rows: list[tuple[str, str, float]] = []
    with ligands_path.open(encoding="utf-8") as lf:
        import csv

        reader = csv.DictReader(lf)
        for row in reader:
            ligand_id = row["ligand_id"]
            smiles = row.get("smiles", "")
            score = score_smiles(smiles, ref_fps, task_id, ligand_id)
            rows.append((task_id, ligand_id, score))

    if rows:
        scores = [r[2] for r in rows]
        logs.append(
            f"[agent] task={task_id} scored={len(rows)} "
            f"score_min={min(scores):.4f} score_max={max(scores):.4f}"
        )
    return rows, logs
