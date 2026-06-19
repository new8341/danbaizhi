"""Build DrugCLIP-compatible LMDB from benchmark ligands and pockets."""
from __future__ import annotations

import os
import pickle
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import lmdb
import numpy as np
from rdkit import Chem
from rdkit.Chem import AllChem


def smiles_to_mol_record(smiles: str, num_conf: int = 1) -> dict | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    try:
        conf_ids = AllChem.EmbedMultipleConfs(mol, num_conf, params)
    except TypeError:
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


def _row_to_record(row: dict[str, str], num_conf: int) -> dict | None:
    rec = smiles_to_mol_record(row["smiles"], num_conf=num_conf)
    if rec is None:
        return None
    # DrugCLIP retrieval returns mol_names from the "smi" field — use ligand_id.
    rec["smi"] = row["ligand_id"]
    return rec


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


def build_mol_lmdb_from_rows(
    ligand_rows: list[dict[str, str]],
    lmdb_path: Path,
    *,
    num_conf: int = 1,
    workers: int = 0,
) -> int:
    num_conf = int(os.environ.get("DRUGCLIP_NUM_CONF", str(num_conf)))
    workers = workers or int(os.environ.get("DRUGCLIP_LMDB_WORKERS", "0"))

    records: list[dict] = []
    if workers <= 1:
        for row in ligand_rows:
            rec = _row_to_record(row, num_conf)
            if rec is not None:
                records.append(rec)
    else:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = {
                pool.submit(_row_to_record, row, num_conf): row["ligand_id"]
                for row in ligand_rows
            }
            for fut in as_completed(futures):
                rec = fut.result()
                if rec is not None:
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
