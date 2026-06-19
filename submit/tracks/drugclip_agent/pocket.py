"""6Å binding pocket around co-crystal ligand (DUD-E + LIT-PCBA)."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from biopandas.mol2 import PandasMol2
from biopandas.pdb import PandasPdb

from submit.tracks.drugclip_agent.benchmark import TaskInfo


@dataclass(frozen=True)
class PocketRecord:
    pocket_id: str
    pocket_atoms: list[str]
    pocket_coordinates: list[list[float]]


def _residue_keys_pdb(pdb_path: Path) -> tuple[np.ndarray, list[str], list[str]]:
    atoms = PandasPdb().read_pdb(str(pdb_path)).df["ATOM"]
    coord = atoms[["x_coord", "y_coord", "z_coord"]].to_numpy(dtype=float)
    residue = (atoms["chain_id"].astype(str) + "_" + atoms["residue_number"].astype(str)).tolist()
    return coord, residue, atoms["atom_name"].tolist()


def _residue_keys_mol2(mol2_path: Path) -> tuple[np.ndarray, list[str], list[str]]:
    df = PandasMol2().read_mol2(str(mol2_path)).df
    coord = df[["x", "y", "z"]].to_numpy(dtype=float)
    residue = (df["subst_name"].astype(str) + "_" + df["residue_id"].astype(str)).tolist()
    return coord, residue, df["atom_name"].tolist()


def _ligand_coords(mol2_path: Path) -> np.ndarray:
    return PandasMol2().read_mol2(str(mol2_path)).df[["x", "y", "z"]].to_numpy(dtype=float)


def _pocket_residues(
    protein_coord: np.ndarray,
    protein_residue: list[str],
    ligand_coord: np.ndarray,
    radius: float,
) -> set[str]:
    pocket: set[str] = set()
    for i, res in enumerate(protein_residue):
        d = np.linalg.norm(protein_coord[i] - ligand_coord[:, None, :], axis=-1).min()
        if d < radius:
            pocket.add(res)
    return pocket


def _extract_pair(protein: Path, ligand: Path, pocket_id: str, radius: float) -> PocketRecord:
    if protein.suffix.lower() == ".pdb":
        p_coord, p_res, p_atom = _residue_keys_pdb(protein)
    else:
        p_coord, p_res, p_atom = _residue_keys_mol2(protein)
    lig_coord = _ligand_coords(ligand)
    pocket_res = _pocket_residues(p_coord, p_res, lig_coord, radius)
    atoms: list[str] = []
    coords: list[list[float]] = []
    for i, res in enumerate(p_res):
        if res in pocket_res:
            sym = p_atom[i][0] if p_atom[i] else "C"
            sym = "C" if sym.isdigit() else sym
            atoms.append(sym)
            coords.append(p_coord[i].tolist())
    if not atoms:
        raise ValueError(f"empty pocket for {pocket_id}")
    return PocketRecord(pocket_id=pocket_id, pocket_atoms=atoms, pocket_coordinates=coords)


def _litpcba_pairs(task: TaskInfo) -> list[tuple[Path, Path, str]]:
    pairs: list[tuple[Path, Path, str]] = []
    for rec_rel in task.receptor_files:
        rec_path = task.resolve(rec_rel)
        stem = rec_path.stem.replace("_protein", "")
        lig_rel = f"refs/{stem}_ligand.mol2"
        if lig_rel not in task.reference_ligand_files:
            for ref in task.reference_ligand_files:
                if stem in ref:
                    lig_rel = ref
                    break
        pairs.append((rec_path, task.resolve(lig_rel), stem))
    return pairs


def extract_task_pockets(task: TaskInfo, radius: float = 6.0) -> list[PocketRecord]:
    if task.benchmark == "LIT-PCBA":
        return [
            _extract_pair(protein, ligand, f"{task.task_id}_{stem}", radius)
            for protein, ligand, stem in _litpcba_pairs(task)
        ]
    return [
        _extract_pair(
            task.resolve(task.receptor_files[0]),
            task.resolve(task.reference_ligand_files[0]),
            task.task_id,
            radius,
        )
    ]


def max_pocket_atom_count(task: TaskInfo, radius: float = 6.0) -> int:
    try:
        return max(len(p.pocket_atoms) for p in extract_task_pockets(task, radius))
    except Exception:
        return 0
