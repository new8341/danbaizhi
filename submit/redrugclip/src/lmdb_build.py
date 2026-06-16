"""Build DrugCLIP-compatible LMDB from SMILES (for optional DrugCLIP inference)."""

from __future__ import annotations

import pickle
from pathlib import Path

import lmdb
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem
from tqdm import tqdm


def smiles_to_mol_record(smiles: str, num_conf: int = 1) -> dict | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    conf_ids = AllChem.EmbedMultipleConfs(
        mol, numConfs=num_conf, params=params, maxAttempts=50
    )
    if not conf_ids:
        return None
    try:
        AllChem.MMFFOptimizeMoleculeConfs(mol, maxIters=200)
    except Exception:
        pass
    mol = Chem.RemoveHs(mol)
    if mol.GetNumConformers() == 0:
        return None
    coords = [
        np.array(mol.GetConformer(i).GetPositions(), dtype=np.float32)
        for i in range(mol.GetNumConformers())
    ]
    atoms = [a.GetSymbol() for a in mol.GetAtoms()]
    return {
        "atoms": atoms,
        "coordinates": coords,
        "smi": Chem.MolToSmiles(mol),
    }


def write_lmdb(records: list[dict], lmdb_path: Path) -> int:
    lmdb_path.parent.mkdir(parents=True, exist_ok=True)
    env = lmdb.open(
        str(lmdb_path),
        subdir=False,
        readonly=False,
        lock=False,
        readahead=False,
        meminit=False,
        map_size=1099511627776,
    )
    n = 0
    with env.begin(write=True) as txn:
        for rec in records:
            txn.put(str(n).encode("ascii"), pickle.dumps(rec))
            n += 1
    env.close()
    return n


def build_mol_lmdb_from_csv(
    ligand_rows: list[dict[str, str]],
    lmdb_path: Path,
    show_progress: bool = False,
) -> int:
    records: list[dict] = []
    iterator = ligand_rows
    if show_progress:
        iterator = tqdm(ligand_rows, desc="conformers", leave=False)
    for row in iterator:
        rec = smiles_to_mol_record(row["smiles"])
        if rec is not None:
            rec["ligand_id"] = row["ligand_id"]
            records.append(rec)
    return write_lmdb(records, lmdb_path)


def build_pocket_lmdb(pockets: list, lmdb_path: Path) -> int:
    records = [
        {
            "pocket": p.pocket_id,
            "pocket_atoms": p.pocket_atoms,
            "pocket_coordinates": p.pocket_coordinates,
        }
        for p in pockets
    ]
    return write_lmdb(records, lmdb_path)
