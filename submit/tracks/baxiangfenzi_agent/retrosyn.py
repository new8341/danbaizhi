"""Retrosynthesis route planner (amide / BRICS + commercial leaves)."""
from __future__ import annotations

import os
from functools import lru_cache

from rdkit import Chem
from rdkit.Chem import AllChem, BRICS

from submit.pack_submission import emit_error
from submit.tracks.baxiangfenzi_agent.chemistry import (
    canonical_smiles,
    commercial_building_blocks,
    is_commercial_fragment,
    is_valid_molecule,
    reaction_atom_balanced,
    strip_brics_dummy,
)


def _bond_indices(mol: Chem.Mol) -> list[int]:
    indices: list[int] = []
    for item in BRICS.FindBRICSBonds(mol):
        if isinstance(item, tuple) and len(item) >= 1:
            atoms = item[0] if isinstance(item[0], tuple) else item
            if isinstance(atoms, tuple) and len(atoms) == 2:
                bond = mol.GetBondBetweenAtoms(int(atoms[0]), int(atoms[1]))
                if bond is not None:
                    indices.append(bond.GetIdx())
    return indices


def _brics_fragments(smiles: str) -> list[tuple[str, str]]:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []
    pairs: list[tuple[str, str]] = []
    for bond_idx in _bond_indices(mol):
        try:
            broken = Chem.FragmentOnBonds(mol, [bond_idx], dummyLabels=((1, 1),))
        except Exception:
            continue
        frags = Chem.GetMolFrags(broken, asMols=True, sanitizeFrags=False)
        if len(frags) != 2:
            continue
        smis: list[str] = []
        for frag in frags:
            try:
                Chem.SanitizeMol(frag)
                cleaned = strip_brics_dummy(Chem.MolToSmiles(frag))
                if cleaned and is_valid_molecule(cleaned):
                    smis.append(cleaned)
            except Exception:
                smis = []
                break
        if len(smis) == 2:
            pairs.append((smis[0], smis[1]))
    return pairs


def _amide_one_step(target: str) -> str | None:
    """Forward-validate amide coupling from commercial acid + amine."""
    mol = Chem.MolFromSmiles(target)
    if mol is None or not mol.HasSubstructMatch(Chem.MolFromSmarts("[C:1](=[O:2])[N:3]")):
        return None
    rxn = AllChem.ReactionFromSmarts("[C:1](=[O:2])[O;H1].[N:3]>>[C:1](=[O:2])[N:3]")
    blocks = commercial_building_blocks()
    acid_pat = Chem.MolFromSmarts("C(=O)[OD1]")
    def _is_amine(smi: str) -> bool:
        mol = Chem.MolFromSmiles(smi)
        if mol is None:
            return False
        return mol.HasSubstructMatch(Chem.MolFromSmarts("[NH2,NH1]")) and not mol.HasSubstructMatch(
            Chem.MolFromSmarts("NC=O")
        )

    acids = [s for s in blocks if Chem.MolFromSmiles(s).HasSubstructMatch(acid_pat)]
    amines = [s for s in blocks if _is_amine(s)]
    for acid in acids:
        for amine in amines:
            try:
                outcomes = rxn.RunReactants(
                    (Chem.MolFromSmiles(acid), Chem.MolFromSmiles(amine))
                )
            except Exception:
                continue
            for outcome in outcomes:
                try:
                    Chem.SanitizeMol(outcome[0])
                    prod = Chem.MolToSmiles(outcome[0], canonical=True)
                except Exception:
                    continue
                if prod == target:
                    step = f"{acid}.{amine}>>{target}"
                    if reaction_atom_balanced([acid, amine], target):
                        return step
    return None


def _suzuki_one_step(target: str) -> str | None:
    rxn = AllChem.ReactionFromSmarts("[c:1]:[c:2][Br].[c:3]:[c:4]B(O)O>>[c:1]:[c:2]-[c:3]:[c:4]")
    blocks = commercial_building_blocks()
    halides = [s for s in blocks if "Br" in Chem.MolToSmiles(Chem.MolFromSmiles(s))]
    boronics = [s for s in blocks if "B(O)O" in s or "B(O)" in s]
    for hal in halides:
        for bor in boronics:
            try:
                outcomes = rxn.RunReactants((Chem.MolFromSmiles(hal), Chem.MolFromSmiles(bor)))
            except Exception:
                continue
            for outcome in outcomes:
                try:
                    Chem.SanitizeMol(outcome[0])
                    prod = Chem.MolToSmiles(outcome[0], canonical=True)
                except Exception:
                    continue
                if prod == target:
                    step = f"{hal}.{bor}>>{target}"
                    if reaction_atom_balanced([hal, bor], target):
                        return step
    return None


def _one_step(target: str) -> str | None:
    amide = _amide_one_step(target)
    if amide:
        return amide
    suzuki = _suzuki_one_step(target)
    if suzuki:
        return suzuki
    for left, right in _brics_fragments(target):
        if is_commercial_fragment(left) and is_commercial_fragment(right):
            step = f"{left}.{right}>>{target}"
            if reaction_atom_balanced([left, right], target):
                return step
    return None


def _two_step(target: str) -> str | None:
    for left, right in _brics_fragments(target):
        if not is_commercial_fragment(left):
            sub = _one_step(left)
            if sub and is_commercial_fragment(right):
                inter = sub.split(">>")[-1]
                step2 = f"{inter}.{right}>>{target}"
                if reaction_atom_balanced([inter, right], target):
                    return f"{sub},{step2}"
        if not is_commercial_fragment(right):
            sub = _one_step(right)
            if sub and is_commercial_fragment(left):
                inter = sub.split(">>")[-1]
                step2 = f"{left}.{inter}>>{target}"
                if reaction_atom_balanced([left, inter], target):
                    return f"{sub},{step2}"
    return None


@lru_cache(maxsize=4096)
def _plan_cached(canonical_target: str) -> str | None:
    if is_commercial_fragment(canonical_target):
        return None
    route = _two_step(canonical_target)
    if route:
        return route
    return _one_step(canonical_target)


def try_plan_route(target_smiles: str) -> str | None:
    can = canonical_smiles(target_smiles)
    if can is None:
        return None
    route = _plan_cached(can)
    if route is None or not validate_route(route, can):
        route = _one_step(can)
    if route is None or not validate_route(route, can):
        return None
    last_product = route.split(">>")[-1]
    if canonical_smiles(last_product) != can:
        route = f"{route},{last_product}>>{can}"
    return route


def plan_route(target_smiles: str) -> str:
    route = try_plan_route(target_smiles)
    if route is None:
        can = canonical_smiles(target_smiles) or target_smiles
        emit_error("BAXIANG_ROUTE_FAILED", f"Could not plan valid route for {can}")
    return route


def validate_route(route: str, target_smiles: str) -> bool:
    can = canonical_smiles(target_smiles)
    if can is None:
        return False
    steps = route.split(",")
    last = steps[-1].split(">>")
    if len(last) != 2:
        return False
    final = canonical_smiles(last[1])
    if final != can:
        return False
    for step in steps:
        lhs, rhs = step.split(">>")
        reactants = lhs.split(".")
        if rhs in reactants:
            return False
        if not reaction_atom_balanced(reactants, rhs):
            return False
    return True


def _route_validity_score(route: str) -> float:
    steps = [s for s in route.split(",") if s.strip()]
    if not steps:
        return 0.0
    for step in steps:
        if ">>" not in step:
            return 0.0
        lhs, rhs = step.split(">>")
        reactants = lhs.split(".")
        for smi in reactants + [rhs]:
            if not is_valid_molecule(smi):
                return 0.0
        if rhs in reactants:
            return 0.0
        if not reaction_atom_balanced(reactants, rhs):
            return 0.0
    return 1.0


def _starting_material_score(route: str) -> float:
    steps = route.split(",")
    if not steps:
        return 0.0
    first = steps[0].split(">>")[0].split(".")
    if not first:
        return 0.0
    hits = sum(1 for smi in first if is_commercial_fragment(smi))
    return hits / len(first)


def _step_penalty_score(route: str) -> float:
    n = len([s for s in route.split(",") if s.strip()])
    return max(0.0, 1.0 - 0.12 * max(0, n - 1))


def _convergence_score(route: str) -> float:
    """Bonus when a step merges two non-commercial intermediates."""
    blocks = commercial_building_blocks()
    for step in route.split(","):
        lhs, _rhs = step.split(">>")
        reactants = lhs.split(".")
        if len(reactants) < 2:
            continue
        non_commercial = [r for r in reactants if canonical_smiles(r) not in blocks]
        if len(non_commercial) >= 2:
            return 1.0
    return 0.0


def _balance_score(route: str) -> float:
    for step in route.split(","):
        lhs, rhs = step.split(">>")
        if not reaction_atom_balanced(lhs.split("."), rhs):
            return 0.0
    return 1.0


def score_route(route: str, target_smiles: str) -> float:
    """Platform route sub-score in [0, 1] (weights per readme)."""
    if not validate_route(route, target_smiles):
        return 0.0
    balance = _balance_score(route)
    if balance <= 0.0:
        return 0.0
    validity = _route_validity_score(route)
    return (
        0.55 * validity
        + 0.30 * _starting_material_score(route)
        + 0.05 * _step_penalty_score(route)
        + 0.05 * _convergence_score(route)
        + 0.05 * balance
    )


def score_molecule(
    smiles: str,
    affinity: float | None,
    sa: float,
    pseudo_affinity: float,
) -> float:
    """Platform molecule sub-score in [0, 1] (binding 0.8 + validity 0.1 + SA 0.1)."""
    if not is_valid_molecule(smiles):
        return 0.0
    aff = affinity if affinity is not None else pseudo_affinity
    binding = max(0.0, min(1.0, (-aff - 4.0) / 8.0))
    sa_part = max(0.0, (4.0 - sa) / 4.0) if sa < 4.0 else 0.0
    return 0.8 * binding + 0.1 * 1.0 + 0.1 * sa_part


def official_composite(molecule_score: float, route_score: float) -> float:
    """复赛官方权重：分子 0.6 + 路线 0.4（documen/Baxiangfenzi/readme.md）。"""
    mol_w = float(os.environ.get("BAXIANG_MOL_WEIGHT", "0.6"))
    route_w = 1.0 - mol_w
    return mol_w * molecule_score + route_w * route_score


def best_route_for_target(target_smiles: str) -> tuple[str | None, float]:
    """Return highest score_route among one- and two-step plans."""
    can = canonical_smiles(target_smiles)
    if can is None:
        return None, 0.0
    routes: list[str] = []
    for planner in (_one_step, _two_step):
        route = planner(can)
        if route and validate_route(route, can):
            routes.append(route)
    if not routes:
        return None, 0.0
    best = max(routes, key=lambda r: score_route(r, can))
    return best, score_route(best, can)
