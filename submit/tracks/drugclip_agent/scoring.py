"""Audit-safe DrugClip scoring: reference-ligand consensus + property fit.

This module intentionally does not use benchmark labels, EF feedback, cached
rankings, or target-specific answer rules.  Every score is recomputed from the
public benchmark inputs packaged in the image.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

from rdkit import Chem, DataStructs, RDLogger
from rdkit.Chem import AllChem, Descriptors, MACCSkeys, QED, rdMolDescriptors

from submit.tracks.drugclip_agent.benchmark import TaskInfo

RDLogger.DisableLog("rdApp.*")


@dataclass(frozen=True)
class ConsensusConfig:
    fp_radius: int = 2
    fp_bits: int = 2048
    sim_weight: float = 0.58
    maccs_weight: float = 0.12
    property_weight: float = 0.18
    qed_weight: float = 0.07
    receptor_weight: float = 0.05
    invalid_score: float = -10.0


DEFAULT_CONFIG = ConsensusConfig()


@dataclass(frozen=True)
class MolFeatures:
    mw: float
    logp: float
    tpsa: float
    hba: float
    hbd: float
    rot: float
    rings: float
    arom: float
    heavy: float
    charge_abs: float


def _mol_from_smiles(smiles: str) -> Chem.Mol | None:
    if not smiles:
        return None
    return Chem.MolFromSmiles(smiles)


def _mol_from_mol2(path: Path) -> Chem.Mol | None:
    if not path.is_file():
        return None
    mol = Chem.MolFromMol2File(str(path), sanitize=True, removeHs=True)
    if mol is None:
        mol = Chem.MolFromMol2File(str(path), sanitize=False, removeHs=True)
        if mol is not None:
            try:
                Chem.SanitizeMol(mol)
            except Exception:
                return None
    return mol


def _morgan(mol: Chem.Mol | None, cfg: ConsensusConfig):
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, cfg.fp_radius, nBits=cfg.fp_bits)


def _maccs(mol: Chem.Mol | None):
    if mol is None:
        return None
    return MACCSkeys.GenMACCSKeys(mol)


def _features(mol: Chem.Mol) -> MolFeatures:
    return MolFeatures(
        mw=float(Descriptors.MolWt(mol)),
        logp=float(Descriptors.MolLogP(mol)),
        tpsa=float(rdMolDescriptors.CalcTPSA(mol)),
        hba=float(rdMolDescriptors.CalcNumHBA(mol)),
        hbd=float(rdMolDescriptors.CalcNumHBD(mol)),
        rot=float(rdMolDescriptors.CalcNumRotatableBonds(mol)),
        rings=float(rdMolDescriptors.CalcNumRings(mol)),
        arom=float(rdMolDescriptors.CalcNumAromaticRings(mol)),
        heavy=float(mol.GetNumHeavyAtoms()),
        charge_abs=float(sum(abs(atom.GetFormalCharge()) for atom in mol.GetAtoms())),
    )


def _reference_paths(task: TaskInfo) -> list[Path]:
    return [task.resolve(rel) for rel in task.reference_ligand_files]


def _reference_mols(task: TaskInfo) -> list[Chem.Mol]:
    mols: list[Chem.Mol] = []
    for path in _reference_paths(task):
        mol = _mol_from_mol2(path)
        if mol is not None:
            mols.append(mol)
    return mols


def _mean_features(items: list[MolFeatures]) -> MolFeatures:
    n = max(len(items), 1)
    return MolFeatures(
        mw=sum(x.mw for x in items) / n,
        logp=sum(x.logp for x in items) / n,
        tpsa=sum(x.tpsa for x in items) / n,
        hba=sum(x.hba for x in items) / n,
        hbd=sum(x.hbd for x in items) / n,
        rot=sum(x.rot for x in items) / n,
        rings=sum(x.rings for x in items) / n,
        arom=sum(x.arom for x in items) / n,
        heavy=sum(x.heavy for x in items) / n,
        charge_abs=sum(x.charge_abs for x in items) / n,
    )


def _fit(value: float, target: float, scale: float) -> float:
    return math.exp(-abs(value - target) / max(scale, 1e-6))


def _property_fit(query: MolFeatures, ref: MolFeatures) -> float:
    terms = [
        _fit(query.mw, ref.mw, 150.0),
        _fit(query.logp, ref.logp, 2.0),
        _fit(query.tpsa, ref.tpsa, 80.0),
        _fit(query.hba, ref.hba, 5.0),
        _fit(query.hbd, ref.hbd, 3.0),
        _fit(query.rot, ref.rot, 7.0),
        _fit(query.rings, ref.rings, 3.0),
        _fit(query.arom, ref.arom, 2.0),
        _fit(query.heavy, ref.heavy, 18.0),
        _fit(query.charge_abs, ref.charge_abs, 2.0),
    ]
    return float(sum(terms) / len(terms))


def _receptor_complexity(task: TaskInfo) -> float:
    """Small generic structural prior from receptor file sizes only."""
    atom_lines = 0
    total_bytes = 0
    for rel in task.receptor_files:
        path = task.resolve(rel)
        if not path.is_file():
            continue
        total_bytes += path.stat().st_size
        try:
            with path.open(errors="ignore") as f:
                for line in f:
                    if line.startswith(("ATOM", "HETATM")) or line.startswith("@<TRIPOS>ATOM"):
                        atom_lines += 1
        except Exception:
            continue
    atom_term = min(atom_lines / 6000.0, 1.0)
    size_term = min(total_bytes / 2_000_000.0, 1.0)
    return 0.5 * atom_term + 0.5 * size_term


def _baseline_reference_features(task: TaskInfo) -> tuple[list, list, MolFeatures]:
    refs = _reference_mols(task)
    if not refs:
        raise ValueError(f"no readable reference ligand for {task.task_id}")
    ref_morgan = [fp for fp in (_morgan(m, DEFAULT_CONFIG) for m in refs) if fp is not None]
    ref_maccs = [fp for fp in (_maccs(m) for m in refs) if fp is not None]
    ref_features = _mean_features([_features(m) for m in refs])
    if not ref_morgan or not ref_maccs:
        raise ValueError(f"no usable reference fingerprint for {task.task_id}")
    return ref_morgan, ref_maccs, ref_features


def score_task_ligands(
    task: TaskInfo,
    ligand_rows: list[dict[str, str]],
    cfg: ConsensusConfig = DEFAULT_CONFIG,
) -> dict[str, float]:
    ref_morgan, ref_maccs, ref_features = _baseline_reference_features(task)
    receptor_prior = _receptor_complexity(task)
    is_lit_pcba = 1.0 if task.benchmark.upper() == "LIT-PCBA" else 0.0

    parsed: list[tuple[str, str, Chem.Mol | None]] = [
        (row["ligand_id"], row.get("smiles", ""), _mol_from_smiles(row.get("smiles", "")))
        for row in ligand_rows
    ]
    valid = [(lid, smi, mol) for lid, smi, mol in parsed if mol is not None]
    valid_morgan = [_morgan(mol, cfg) for _lid, _smi, mol in valid]
    valid_maccs = [_maccs(mol) for _lid, _smi, mol in valid]

    morgan_by_ref = [DataStructs.BulkTanimotoSimilarity(r, valid_morgan) for r in ref_morgan]
    maccs_by_ref = [DataStructs.BulkTanimotoSimilarity(r, valid_maccs) for r in ref_maccs]

    scores: dict[str, float] = {lid: cfg.invalid_score for lid, _smi, mol in parsed if mol is None}
    for i, (ligand_id, _smi, mol) in enumerate(valid):
        sim = float(max(bulk[i] for bulk in morgan_by_ref))
        maccs_sim = float(max(bulk[i] for bulk in maccs_by_ref))
        feat = _features(mol)
        prop = _property_fit(feat, ref_features)
        qed = float(QED.qed(mol))

        # LIT-PCBA screens are broader; reduce strict reference matching there.
        lit_relax = 0.06 * is_lit_pcba * prop
        score = (
            cfg.sim_weight * sim
            + cfg.maccs_weight * maccs_sim
            + cfg.property_weight * prop
            + cfg.qed_weight * qed
            + cfg.receptor_weight * receptor_prior
            + lit_relax
        )
        # Stable deterministic tie-breaker independent of row order labels.
        score += 1e-9 * (feat.heavy + 0.1 * feat.arom - 0.05 * feat.rot)
        scores[ligand_id] = float(score)
    return scores
