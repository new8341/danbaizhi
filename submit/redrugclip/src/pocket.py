"""Extract binding pockets (6A around reference ligand) for DUD-E and LIT-PCBA tasks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
from biopandas.mol2 import PandasMol2
from biopandas.pdb import PandasPdb

from src.benchmark import TaskInfo


@dataclass(frozen=True)
class PocketRecord:
    pocket_id: str
    pocket_atoms: list[str]
    pocket_coordinates: list[list[float]]


def _residue_keys_pdb(pdb_path: Path) -> tuple[np.ndarray, list[str], list[str]]:
    pdb_df = PandasPdb().read_pdb(str(pdb_path))
    atoms = pdb_df.df["ATOM"]
    coord = atoms[["x_coord", "y_coord", "z_coord"]].to_numpy(dtype=float)
    residue_name = (
        atoms["chain_id"].astype(str) + "_" + atoms["residue_number"].astype(str)
    ).tolist()
    atom_name = atoms["atom_name"].tolist()
    return coord, residue_name, atom_name


def _coords_mol2(mol2_path: Path) -> tuple[np.ndarray, list[str]]:
    df = PandasMol2().read_mol2(str(mol2_path)).df
    coord = df[["x", "y", "z"]].to_numpy(dtype=float)
    atom_name = df["atom_name"].tolist()
    return coord, atom_name


def _residue_keys_mol2(mol2_path: Path) -> tuple[np.ndarray, list[str], list[str]]:
    df = PandasMol2().read_mol2(str(mol2_path)).df
    coord = df[["x", "y", "z"]].to_numpy(dtype=float)
    residue_name = (df["subst_name"].astype(str) + "_" + df["residue_id"].astype(str)).tolist()
    atom_name = df["atom_name"].tolist()
    return coord, residue_name, atom_name


def _pocket_residues(
    protein_coord: np.ndarray,
    protein_residue: list[str],
    ligand_coord: np.ndarray,
    radius: float = 6.0,
) -> set[str]:
    pocket: set[str] = set()
    for i, res in enumerate(protein_residue):
        d = np.linalg.norm(protein_coord[i] - ligand_coord[:, None, :], axis=-1).min()
        if d < radius:
            pocket.add(res)
    return pocket


def extract_pocket_from_pair(
    protein_path: Path,
    ligand_path: Path,
    pocket_id: str,
    radius: float = 6.0,
) -> PocketRecord:
    suffix = protein_path.suffix.lower()
    if suffix == ".pdb":
        p_coord, p_res, p_atom = _residue_keys_pdb(protein_path)
    elif suffix == ".mol2":
        p_coord, p_res, p_atom = _residue_keys_mol2(protein_path)
    else:
        raise ValueError(f"unsupported protein format: {protein_path}")

    l_coord, _ = _coords_mol2(ligand_path)
    pocket_res = _pocket_residues(p_coord, p_res, l_coord, radius=radius)

    atoms: list[str] = []
    coords: list[list[float]] = []
    for i, res in enumerate(p_res):
        if res in pocket_res:
            sym = p_atom[i][0] if p_atom[i] else "C"
            if sym.isdigit():
                sym = "C"
            atoms.append(sym)
            coords.append(p_coord[i].tolist())

    if not atoms:
        raise ValueError(f"empty pocket for {pocket_id} ({protein_path})")

    return PocketRecord(pocket_id=pocket_id, pocket_atoms=atoms, pocket_coordinates=coords)


def pair_litpcba_receptors(task: TaskInfo) -> list[tuple[Path, Path, str]]:
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
        lig_path = task.resolve(lig_rel)
        pairs.append((rec_path, lig_path, stem))
    return pairs


def extract_task_pockets(task: TaskInfo, radius: float = 6.0) -> list[PocketRecord]:
    if task.benchmark == "DUD-E":
        protein = task.resolve(task.receptor_files[0])
        ligand = task.resolve(task.reference_ligand_files[0])
        return [
            extract_pocket_from_pair(
                protein, ligand, pocket_id=task.task_id, radius=radius
            )
        ]

    pockets: list[PocketRecord] = []
    for protein, ligand, stem in pair_litpcba_receptors(task):
        pockets.append(
            extract_pocket_from_pair(
                protein, ligand, pocket_id=f"{task.task_id}_{stem}", radius=radius
            )
        )
    return pockets
