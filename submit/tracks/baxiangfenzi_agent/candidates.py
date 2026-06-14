"""Enumerate drug-like candidates via RDKit reactions (runtime generation)."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem

from submit.tracks.baxiangfenzi_agent.chemistry import canonical_smiles, is_valid_molecule, sa_score


def _seed_from_target(pdb_path: Path) -> int:
    digest = hashlib.sha256(pdb_path.read_bytes()).hexdigest()
    return int(digest[:8], 16)


def _run_reaction(smarts: str, reactants: list[str]) -> list[str]:
    rxn = AllChem.ReactionFromSmarts(smarts)
    products: list[str] = []
    mols = []
    for smi in reactants:
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return []
        mols.append(m)
    try:
        outcomes = rxn.RunReactants(tuple(mols))
    except Exception:
        return []
    for outcome in outcomes:
        for mol in outcome:
            try:
                Chem.SanitizeMol(mol)
                smi = Chem.MolToSmiles(mol, canonical=True)
                products.append(smi)
            except Exception:
                continue
    return products


def _mutate_smiles(smiles: str, seed: int, variants: int = 4) -> list[str]:
    rxn = AllChem.ReactionFromSmarts("[c:1][cH1:2]>>[c:1][c:2]F")
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    out: list[str] = []
    try:
        for outcome in rxn.RunReactants((mol,))[:variants]:
            for prod in outcome:
                try:
                    Chem.SanitizeMol(prod)
                    out.append(Chem.MolToSmiles(prod, canonical=True))
                except Exception:
                    continue
    except Exception:
        return []
    return out


def generate_candidates(pdb_path: Path, max_candidates: int | None = None) -> list[str]:
    limit = max_candidates or int(os.environ.get("BAXIANG_MAX_CANDIDATES", "120"))
    seed = _seed_from_target(pdb_path)

    halides = [
        "Brc1ccccc1",
        "Brc1cccnc1",
        "Brc1ccc(O)cc1",
        "Brc1ccc(F)cc1",
        "Brc1ccc(C)cc1",
        "Brc1ccc2[nH]ccc2c1",
        "Clc1cccnc1",
        "Ic1ccccc1",
    ]
    boronics = [
        "OB(O)c1ccccc1",
        "COc1ccc(B(O)O)cc1",
        "Fc1ccc(B(O)O)cc1",
        "Cc1ccc(B(O)O)cc1",
        "Nc1ccc(B(O)O)cc1",
    ]
    amines = ["Nc1ccccc1", "Nc1cccnc1", "C1CCNC1", "CCN", "c1ccc(N)cc1"]
    acids = ["CC(=O)O", "OC(=O)c1ccccc1", "OC(=O)c1cccnc1"]

    candidates: set[str] = set()

    suzuki = "[c:1]:[c:2][Br].[c:3]:[c:4]B(O)O>>[c:1]:[c:2]-[c:3]:[c:4]"
    for i, h in enumerate(halides):
        for j, b in enumerate(boronics):
            for smi in _run_reaction(suzuki, [h, b]):
                candidates.add(smi)
            if len(candidates) >= limit * 2:
                break
        if len(candidates) >= limit * 2:
            break

    amide = "[C:1](=[O:2])[O;H1].[N:3]>>[C:1](=[O:2])[N:3]"
    for a in acids:
        for n in amines:
            for smi in _run_reaction(amide, [a, n]):
                candidates.add(smi)

    seeds = list(candidates)[:12]
    for k, base in enumerate(seeds):
        for smi in _mutate_smiles(base, seed + k, variants=2):
            candidates.add(smi)

    filtered: list[tuple[float, str]] = []
    for smi in candidates:
        if not is_valid_molecule(smi):
            continue
        sa = sa_score(smi)
        if sa >= 4.0:
            continue
        filtered.append((sa, smi))

    filtered.sort(key=lambda x: x[0])
    ordered = [smi for _, smi in filtered]

    if len(ordered) < limit // 3:
        for ring in ("c1ccncc1", "c1ccc2[nH]ccc2c1", "c1ccc2ncccc2c1", "c1ccc2ccccc2c1"):
            for smi in _mutate_smiles(ring, seed + 17, variants=18):
                if is_valid_molecule(smi) and sa_score(smi) < 4.0:
                    ordered.append(canonical_smiles(smi) or smi)

    seen: set[str] = set()
    unique: list[str] = []
    for smi in ordered:
        can = canonical_smiles(smi)
        if can and can not in seen:
            seen.add(can)
            unique.append(can)
        if len(unique) >= limit:
            break
    return unique
