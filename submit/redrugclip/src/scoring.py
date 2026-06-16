"""Ligand scoring strategies for virtual screening (EF1%-oriented)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Literal

import numpy as np
from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, Descriptors, MACCSkeys, QED
from rdkit.Chem import rdMolDescriptors

RDLogger.DisableLog("rdApp.*")

from src.benchmark import TaskInfo
from src.pocket import extract_task_pockets, pair_litpcba_receptors

FpKind = Literal["morgan2", "morgan3", "fcfp", "maccs"]


class AggregateMode(str, Enum):
    MAX = "max"
    MEAN = "mean"
    FIRST = "first"


@dataclass
class ScoringConfig:
    radius: float = 6.0
    fp_radius: int = 2
    fp_bits: int = 2048
    aggregate: AggregateMode = AggregateMode.MAX
    temperature: float = 1.0
    use_qed_bonus: float = 0.0
    use_drug_likeness: bool = False
    # Ensemble / mechanism knobs (rull.md: 推理/排序策略优化)
    fp_kinds: tuple[FpKind, ...] = ("morgan2", "morgan3", "fcfp", "maccs")
    fp_weights: dict[str, float] = field(
        default_factory=lambda: {
            "morgan2": 0.35,
            "morgan3": 0.25,
            "fcfp": 0.30,
            "maccs": 0.10,
        }
    )
    substructure_bonus: float = 0.0
    physchem_bonus: float = 0.0
    pocket_heavy_bonus: float = 0.0
    smiles_sim_weight: float = 0.0


def _mol_from_mol2(ligand_path: Path) -> Chem.Mol | None:
    mol = Chem.MolFromMol2File(str(ligand_path), sanitize=False, removeHs=True)
    if mol is None:
        return None
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        pass
    return mol


def _fp_from_mol(mol: Chem.Mol, kind: FpKind, n_bits: int = 2048):
    try:
        if kind == "morgan2":
            return AllChem.GetMorganFingerprintAsBitVect(mol, 2, nBits=n_bits)
        if kind == "morgan3":
            return AllChem.GetMorganFingerprintAsBitVect(mol, 3, nBits=n_bits)
        if kind == "fcfp":
            return AllChem.GetMorganFingerprintAsBitVect(
                mol, 2, nBits=n_bits, useFeatures=True
            )
        if kind == "maccs":
            return MACCSkeys.GenMACCSKeys(mol)
    except (RuntimeError, ValueError):
        try:
            Chem.SanitizeMol(mol)
            if kind == "maccs":
                return MACCSkeys.GenMACCSKeys(mol)
            r = 3 if kind == "morgan3" else 2
            return AllChem.GetMorganFingerprintAsBitVect(mol, r, nBits=n_bits)
        except Exception:
            return None
    raise ValueError(kind)


def _fp_from_smiles(smiles: str, kind: FpKind, n_bits: int = 2048):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return _fp_from_mol(mol, kind, n_bits)


def _fp_from_mol2(ligand_path: Path, kind: FpKind, n_bits: int = 2048):
    mol = _mol_from_mol2(ligand_path)
    if mol is None:
        return None
    return _fp_from_mol(mol, kind, n_bits)


def _fp_from_smiles_legacy(smiles: str, radius: int, n_bits: int):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def _fp_from_mol2_legacy(ligand_path: Path, radius: int, n_bits: int):
    mol = Chem.MolFromMol2File(str(ligand_path), sanitize=True, removeHs=True)
    if mol is None:
        mol = Chem.MolFromMol2File(str(ligand_path), sanitize=False, removeHs=True)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def _sanitize_mol(mol: Chem.Mol) -> Chem.Mol | None:
    try:
        smi = Chem.MolToSmiles(mol)
        m2 = Chem.MolFromSmiles(smi)
        if m2 is None:
            return None
        Chem.SanitizeMol(m2)
        return m2
    except Exception:
        return None


def _physchem_vector(mol: Chem.Mol) -> np.ndarray:
    m = _sanitize_mol(mol) or mol
    try:
        return np.array(
            [
                Descriptors.MolWt(m),
                Descriptors.MolLogP(m),
                rdMolDescriptors.CalcTPSA(m),
                rdMolDescriptors.CalcNumHBD(m),
                rdMolDescriptors.CalcNumHBA(m),
                rdMolDescriptors.CalcNumRotatableBonds(m),
                rdMolDescriptors.CalcNumAromaticRings(m),
            ],
            dtype=float,
        )
    except Exception:
        return np.array(
            [Descriptors.MolWt(m), Descriptors.MolLogP(m), 0, 0, 0, 0, 0],
            dtype=float,
        )


def _physchem_similarity(q: np.ndarray, r: np.ndarray) -> float:
    """Gaussian kernel on scaled property differences (higher = more similar)."""
    scales = np.array([100.0, 3.0, 50.0, 2.0, 3.0, 5.0, 2.0])
    d2 = np.sum(((q - r) / scales) ** 2)
    return float(np.exp(-0.5 * d2))


def _collect_ref_smiles(task: TaskInfo) -> list[str]:
    smis: list[str] = []
    for m in _collect_ref_mols(task):
        try:
            smis.append(Chem.MolToSmiles(m))
        except Exception:
            pass
    return smis


def _smiles_tanimoto(a: str, b: str) -> float:
    ma, mb = Chem.MolFromSmiles(a), Chem.MolFromSmiles(b)
    if ma is None or mb is None:
        return 0.0
    fa = AllChem.GetMorganFingerprintAsBitVect(ma, 2, nBits=2048)
    fb = AllChem.GetMorganFingerprintAsBitVect(mb, 2, nBits=2048)
    return float(DataStructs.TanimotoSimilarity(fa, fb))


def _collect_ref_mols(task: TaskInfo) -> list[Chem.Mol]:
    mols: list[Chem.Mol] = []
    if task.benchmark == "DUD-E":
        raw = _mol_from_mol2(task.resolve(task.reference_ligand_files[0]))
        m = _sanitize_mol(raw) if raw else None
        if m is not None:
            mols.append(m)
    else:
        for _p, lig, _s in pair_litpcba_receptors(task):
            raw = _mol_from_mol2(lig)
            m = _sanitize_mol(raw) if raw else None
            if m is not None:
                mols.append(m)
    return mols


class BaseScorer(ABC):
    @abstractmethod
    def score_task(
        self,
        task: TaskInfo,
        ligand_rows: list[dict[str, str]],
        config: ScoringConfig,
    ) -> dict[str, float]:
        """Return ligand_id -> score (higher is better)."""


class FingerprintScorer(BaseScorer):
    """Single Morgan FP Tanimoto vs reference ligand(s) — champion-compatible path."""

    def score_task(
        self,
        task: TaskInfo,
        ligand_rows: list[dict[str, str]],
        config: ScoringConfig,
    ) -> dict[str, float]:
        ref_fps = []
        if task.benchmark == "DUD-E":
            ref_path = task.resolve(task.reference_ligand_files[0])
            fp = _fp_from_mol2_legacy(ref_path, config.fp_radius, config.fp_bits)
            if fp is not None:
                ref_fps.append(fp)
        else:
            for _protein, ligand, _stem in pair_litpcba_receptors(task):
                fp = _fp_from_mol2_legacy(ligand, config.fp_radius, config.fp_bits)
                if fp is not None:
                    ref_fps.append(fp)

        if not ref_fps:
            raise ValueError(f"no reference fingerprint for {task.task_id}")

        query_ids: list[str] = []
        query_smiles: list[str] = []
        query_fps: list = []
        for row in ligand_rows:
            query_ids.append(row["ligand_id"])
            query_smiles.append(row["smiles"])
            query_fps.append(
                _fp_from_smiles_legacy(row["smiles"], config.fp_radius, config.fp_bits)
            )

        valid_idx = [i for i, fp in enumerate(query_fps) if fp is not None]
        valid_map = {orig: vi for vi, orig in enumerate(valid_idx)}
        valid_fps = [query_fps[i] for i in valid_idx]
        bulk_by_ref = [
            DataStructs.BulkTanimotoSimilarity(r, valid_fps) for r in ref_fps
        ]

        scores: dict[str, float] = {}
        for i, (lid, smi, qfp) in enumerate(zip(query_ids, query_smiles, query_fps)):
            if qfp is None:
                scores[lid] = 0.0
                continue
            vi = valid_map[i]
            sims_per_ref = [bulk[vi] for bulk in bulk_by_ref]
            if config.aggregate == AggregateMode.MAX:
                raw = float(max(sims_per_ref))
            elif config.aggregate == AggregateMode.MEAN:
                raw = float(np.mean(sims_per_ref))
            else:
                raw = float(sims_per_ref[0])

            if config.use_qed_bonus > 0 or config.use_drug_likeness:
                mol = Chem.MolFromSmiles(smi)
                if mol is not None:
                    if config.use_qed_bonus > 0:
                        raw += config.use_qed_bonus * QED.qed(mol)
                    if config.use_drug_likeness:
                        mw = Descriptors.MolWt(mol)
                        logp = Descriptors.MolLogP(mol)
                        if 150 <= mw <= 500:
                            raw += 0.05
                        if -1 <= logp <= 5:
                            raw += 0.05

            if config.temperature != 1.0:
                raw = raw ** (1.0 / max(config.temperature, 1e-6))
            scores[lid] = raw
        return scores


def _score_fp_task(
    task: TaskInfo,
    ligand_rows: list[dict[str, str]],
    config: ScoringConfig,
    kinds: tuple[FpKind, ...] | None = None,
) -> dict[str, float]:
    kinds = kinds or config.fp_kinds
    ref_fps_by_kind: dict[FpKind, list] = {k: [] for k in kinds}
    if task.benchmark == "DUD-E":
        ref_path = task.resolve(task.reference_ligand_files[0])
        for k in kinds:
            fp = _fp_from_mol2(ref_path, k, config.fp_bits)
            if fp is not None:
                ref_fps_by_kind[k].append(fp)
    else:
        for _protein, ligand, _stem in pair_litpcba_receptors(task):
            for k in kinds:
                fp = _fp_from_mol2(ligand, k, config.fp_bits)
                if fp is not None:
                    ref_fps_by_kind[k].append(fp)

    if not any(ref_fps_by_kind.values()):
        raise ValueError(f"no reference fingerprint for {task.task_id}")

    ref_mols = _collect_ref_mols(task) if config.substructure_bonus > 0 else []
    ref_smiles = _collect_ref_smiles(task) if config.smiles_sim_weight > 0 else []
    ref_pc = (
        np.mean([_physchem_vector(m) for m in ref_mols], axis=0) if ref_mols else None
    )

    pocket_size = 0
    if config.pocket_heavy_bonus > 0:
        try:
            pockets = extract_task_pockets(task, radius=config.radius)
            pocket_size = max(len(p.pocket_atoms) for p in pockets)
        except Exception:
            pass

    query_ids: list[str] = []
    query_smiles: list[str] = []
    query_mols: list[Chem.Mol | None] = []
    query_fps: dict[FpKind, list] = {k: [] for k in kinds}

    for row in ligand_rows:
        query_ids.append(row["ligand_id"])
        smi = row["smiles"]
        query_smiles.append(smi)
        mol = Chem.MolFromSmiles(smi)
        query_mols.append(mol)
        for k in kinds:
            query_fps[k].append(
                _fp_from_mol(mol, k, config.fp_bits) if mol else None
            )

    bulk_cache: dict[FpKind, list[list[float]]] = {}
    for k in kinds:
        refs = ref_fps_by_kind[k]
        if not refs:
            continue
        valid_idx = [i for i, fp in enumerate(query_fps[k]) if fp is not None]
        valid_fps = [query_fps[k][i] for i in valid_idx]
        bulk_cache[k] = [
            DataStructs.BulkTanimotoSimilarity(r, valid_fps) for r in refs
        ]

    valid_maps: dict[FpKind, dict[int, int]] = {}
    for k in kinds:
        valid_idx = [i for i, fp in enumerate(query_fps[k]) if fp is not None]
        valid_maps[k] = {orig: vi for vi, orig in enumerate(valid_idx)}

    scores: dict[str, float] = {}
    for i, (lid, smi, mol) in enumerate(zip(query_ids, query_smiles, query_mols)):
        if mol is None:
            scores[lid] = 0.0
            continue

        weighted_sim = 0.0
        weight_sum = 0.0
        for k in kinds:
            refs = ref_fps_by_kind[k]
            if not refs or k not in bulk_cache:
                continue
            vi = valid_maps[k].get(i)
            if vi is None:
                continue
            sims = [bulk[vi] for bulk in bulk_cache[k]]
            if config.aggregate == AggregateMode.MAX:
                sim = float(max(sims))
            elif config.aggregate == AggregateMode.MEAN:
                sim = float(np.mean(sims))
            else:
                sim = float(sims[0])
            w = config.fp_weights.get(k, 1.0)
            weighted_sim += w * sim
            weight_sum += w

        raw = weighted_sim / max(weight_sum, 1e-9)

        if config.substructure_bonus > 0 and ref_mols:
            q = _sanitize_mol(mol) or mol
            for rm in ref_mols:
                try:
                    if q.HasSubstructMatch(rm):
                        raw += config.substructure_bonus
                        break
                except Exception:
                    continue

        if config.physchem_bonus > 0 and ref_pc is not None:
            raw += config.physchem_bonus * _physchem_similarity(
                _physchem_vector(mol), ref_pc
            )

        if config.smiles_sim_weight > 0 and ref_smiles:
            best_smi = max(
                (_smiles_tanimoto(smi, rs) for rs in ref_smiles), default=0.0
            )
            raw += config.smiles_sim_weight * best_smi

        if config.pocket_heavy_bonus > 0 and pocket_size > 0:
            heavy = mol.GetNumHeavyAtoms()
            raw += config.pocket_heavy_bonus * (
                1.0 - min(abs(heavy - pocket_size * 0.12) / max(heavy, 1), 1.0)
            )

        if config.use_qed_bonus > 0:
            raw += config.use_qed_bonus * QED.qed(mol)
        if config.use_drug_likeness:
            mw = Descriptors.MolWt(mol)
            logp = Descriptors.MolLogP(mol)
            if 150 <= mw <= 500:
                raw += 0.03
            if -1 <= logp <= 5:
                raw += 0.03

        if config.temperature != 1.0:
            raw = raw ** (1.0 / max(config.temperature, 1e-6))

        scores[lid] = raw

    return scores


class EnsembleScorer(BaseScorer):
    """Multi-fingerprint + physchem + substructure (EF1% ranking optimization)."""

    def score_task(
        self,
        task: TaskInfo,
        ligand_rows: list[dict[str, str]],
        config: ScoringConfig,
    ) -> dict[str, float]:
        return _score_fp_task(task, ligand_rows, config, kinds=config.fp_kinds)


class HybridScorer(BaseScorer):
    """Champion (18.87): FingerprintScorer + pocket bonus; optional SMILES tweak for v2."""

    def __init__(self, base: FingerprintScorer | None = None):
        self.base = base or FingerprintScorer()

    def score_task(
        self,
        task: TaskInfo,
        ligand_rows: list[dict[str, str]],
        config: ScoringConfig,
    ) -> dict[str, float]:
        fp_cfg = ScoringConfig(
            radius=config.radius,
            fp_radius=config.fp_radius,
            fp_bits=config.fp_bits,
            aggregate=config.aggregate,
            temperature=config.temperature,
            use_qed_bonus=config.use_qed_bonus,
            use_drug_likeness=config.use_drug_likeness,
        )
        fp_scores = self.base.score_task(task, ligand_rows, fp_cfg)
        try:
            pockets = extract_task_pockets(task, radius=config.radius)
            pocket_size = max(len(p.pocket_atoms) for p in pockets)
        except Exception:
            pocket_size = 0

        ref_smiles = _collect_ref_smiles(task) if config.smiles_sim_weight > 0 else []

        out: dict[str, float] = {}
        for row in ligand_rows:
            lid = row["ligand_id"]
            smi = row["smiles"]
            mol = Chem.MolFromSmiles(smi)
            heavy = mol.GetNumHeavyAtoms() if mol else 0
            bonus = config.pocket_heavy_bonus * (
                1.0 - min(abs(heavy - pocket_size * 0.15) / max(heavy, 1), 1.0)
            )
            if ref_smiles:
                bonus += config.smiles_sim_weight * max(
                    (_smiles_tanimoto(smi, rs) for rs in ref_smiles), default=0.0
                )
            out[lid] = fp_scores[lid] + bonus
        return out


def get_scorer(name: str) -> BaseScorer:
    if name == "fingerprint":
        return FingerprintScorer()
    if name == "ensemble":
        return EnsembleScorer()
    if name == "hybrid":
        return HybridScorer()
    raise ValueError(f"unknown scorer: {name}")
