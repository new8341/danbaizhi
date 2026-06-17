"""hybrid_max_qed: Morgan2 Tanimoto + QED/drug-likeness + pocket heavy-atom bonus."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, Descriptors, QED

from submit.tracks.drugclip_agent.benchmark import TaskInfo
from submit.tracks.drugclip_agent.pocket import _litpcba_pairs, max_pocket_atom_count

RDLogger.DisableLog("rdApp.*")


@dataclass(frozen=True)
class HybridConfig:
    """Champion strategy (ReDrugClip hybrid_max_qed, platform ~18.87 / peak 19.23)."""

    fp_radius: int = 2
    fp_bits: int = 2048
    pocket_radius: float = 6.0
    qed_bonus: float = 0.05
    pocket_heavy_bonus: float = 0.02
    use_drug_likeness: bool = True
    smiles_sim_weight: float = 0.0


DEFAULT_CONFIG = HybridConfig()


def _fp_morgan(mol: Chem.Mol | None, radius: int, n_bits: int):
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def _mol_from_mol2(path: Path) -> Chem.Mol | None:
    mol = Chem.MolFromMol2File(str(path), sanitize=True, removeHs=True)
    if mol is None:
        mol = Chem.MolFromMol2File(str(path), sanitize=False, removeHs=True)
    return mol


def _reference_ligand_paths(task: TaskInfo) -> list[Path]:
    if task.benchmark == "LIT-PCBA":
        return [lig for _p, lig, _s in _litpcba_pairs(task)]
    if task.reference_ligand_files:
        return [task.resolve(task.reference_ligand_files[0])]
    return []


def _reference_fps(task: TaskInfo, cfg: HybridConfig) -> list:
    fps: list = []
    for path in _reference_ligand_paths(task):
        fp = _fp_morgan(_mol_from_mol2(path), cfg.fp_radius, cfg.fp_bits)
        if fp is not None:
            fps.append(fp)
    return fps


def _drug_likeness_bonus(mol: Chem.Mol) -> float:
    bonus = 0.0
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    if 150 <= mw <= 500:
        bonus += 0.05
    if -1 <= logp <= 5:
        bonus += 0.05
    return bonus


def _fingerprint_scores(
    task: TaskInfo,
    ligand_rows: list[dict[str, str]],
    cfg: HybridConfig,
) -> dict[str, float]:
    """Phase 1: Morgan max Tanimoto + QED + drug-likeness (ReDrugClip FingerprintScorer)."""
    ref_fps = _reference_fps(task, cfg)
    if not ref_fps:
        raise ValueError(f"no reference fingerprint for {task.task_id}")

    ids: list[str] = []
    smiles_list: list[str] = []
    query_fps: list = []
    for row in ligand_rows:
        ids.append(row["ligand_id"])
        smi = row["smiles"]
        smiles_list.append(smi)
        query_fps.append(_fp_morgan(Chem.MolFromSmiles(smi), cfg.fp_radius, cfg.fp_bits))

    valid_idx = [i for i, fp in enumerate(query_fps) if fp is not None]
    valid_map = {orig: vi for vi, orig in enumerate(valid_idx)}
    valid_fps = [query_fps[i] for i in valid_idx]
    bulk_by_ref = [DataStructs.BulkTanimotoSimilarity(r, valid_fps) for r in ref_fps]

    scores: dict[str, float] = {}
    for i, (lid, smi, qfp) in enumerate(zip(ids, smiles_list, query_fps)):
        if qfp is None:
            scores[lid] = 0.0
            continue
        vi = valid_map[i]
        raw = float(max(bulk[vi] for bulk in bulk_by_ref))
        mol = Chem.MolFromSmiles(smi)
        if mol is not None:
            raw += cfg.qed_bonus * QED.qed(mol)
            if cfg.use_drug_likeness:
                raw += _drug_likeness_bonus(mol)
        scores[lid] = raw
    return scores


def _hybrid_bonuses(
    task: TaskInfo,
    ligand_rows: list[dict[str, str]],
    cfg: HybridConfig,
    fp_scores: dict[str, float],
) -> dict[str, float]:
    """Phase 2: pocket heavy-atom bonus on every row (ReDrugClip HybridScorer)."""
    try:
        pocket_size = max_pocket_atom_count(task, cfg.pocket_radius)
    except Exception:
        pocket_size = 0

    out: dict[str, float] = {}
    for row in ligand_rows:
        lid = row["ligand_id"]
        smi = row["smiles"]
        mol = Chem.MolFromSmiles(smi)
        heavy = mol.GetNumHeavyAtoms() if mol else 0
        bonus = cfg.pocket_heavy_bonus * (
            1.0 - min(abs(heavy - pocket_size * 0.15) / max(heavy, 1), 1.0)
        )
        out[lid] = fp_scores.get(lid, 0.0) + bonus
    return out


def score_task_ligands(
    task: TaskInfo,
    ligand_rows: list[dict[str, str]],
    cfg: HybridConfig = DEFAULT_CONFIG,
) -> dict[str, float]:
    fp_scores = _fingerprint_scores(task, ligand_rows, cfg)
    return _hybrid_bonuses(task, ligand_rows, cfg, fp_scores)
