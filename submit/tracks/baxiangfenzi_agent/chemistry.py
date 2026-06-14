"""RDKit helpers: validity, SA score, atom balance."""
from __future__ import annotations

import os
import sys
from collections import Counter
from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import Descriptors, Lipinski, rdMolDescriptors

# RDKit contrib SA_Score
from rdkit.Chem import RDConfig

sys.path.append(os.path.join(RDConfig.RDContribDir, "SA_Score"))
import sascorer  # type: ignore[import-not-found]


def canonical_smiles(smiles: str) -> str | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol, canonical=True)


def is_valid_molecule(smiles: str) -> bool:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return False
    if Descriptors.MolWt(mol) < 120 or Descriptors.MolWt(mol) > 650:
        return False
    if Lipinski.NumHDonors(mol) > 6 or Lipinski.NumHAcceptors(mol) > 12:
        return False
    return True


def sa_score(smiles: str) -> float:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 10.0
    return float(sascorer.calculateScore(mol))


def atom_counts(smiles: str) -> Counter[str] | None:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    counts: Counter[str] = Counter()
    for atom in mol.GetAtoms():
        counts[atom.GetSymbol()] += 1
    return counts


def reaction_atom_balanced(reactants: list[str], product: str) -> bool:
    """Product heavy atoms + H must be covered by reactant pool (condensation OK)."""
    left: Counter[str] = Counter()
    for smi in reactants:
        part = atom_counts(smi)
        if part is None:
            return False
        left += part
    right = atom_counts(product)
    if right is None:
        return False
    for elem, cnt in right.items():
        if left.get(elem, 0) < cnt:
            return False
    return True


def strip_brics_dummy(smiles: str) -> str | None:
    """Remove BRICS attachment markers like [16*] -> H."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    rw = Chem.RWMol(mol)
    to_remove: list[int] = []
    for atom in rw.GetAtoms():
        if atom.GetAtomicNum() == 0:
            nbrs = atom.GetNeighbors()
            if nbrs:
                nbrs[0].SetNumExplicitHs(max(1, nbrs[0].GetNumExplicitHs()))
            to_remove.append(atom.GetIdx())
    for idx in sorted(to_remove, reverse=True):
        rw.RemoveAtom(idx)
    try:
        Chem.SanitizeMol(rw)
    except Exception:
        return None
    return Chem.MolToSmiles(rw, canonical=True)


@lru_cache(maxsize=1)
def commercial_building_blocks() -> frozenset[str]:
  """Common purchasable fragments (for retrosynthesis leaves)."""
  raw = [
      "c1ccccc1",
      "Cc1ccccc1",
      "Oc1ccccc1",
      "Fc1ccccc1",
      "Nc1ccccc1",
      "Brc1ccccc1",
      "Clc1ccccc1",
      "Ic1ccccc1",
      "OB(O)c1ccccc1",
      "COc1ccccc1",
      "CC(=O)O",
      "OC(=O)c1ccccc1",
      "OC(=O)c1cccnc1",
      "CC(=O)Cl",
      "CN",
      "COC",
      "CCN",
      "CCOC",
      "C1CCNC1",
      "c1ccncc1",
      "c1cccnc1",
      "c1ccc2ccccc2c1",
  ]
  out: set[str] = set()
  for smi in raw:
        can = canonical_smiles(smi)
        if can:
            out.add(can)
  return frozenset(out)


def is_commercial_fragment(smiles: str) -> bool:
    can = canonical_smiles(smiles)
    if can is None:
        return False
    if can in commercial_building_blocks():
        return True
    return sa_score(can) <= 2.2 and Descriptors.MolWt(Chem.MolFromSmiles(can)) <= 180
