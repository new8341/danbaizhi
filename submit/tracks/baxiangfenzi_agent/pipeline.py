"""Per-target agent loop: generate → dock → select → retrosynthesize."""
from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from submit.tracks.baxiangfenzi_agent.candidates import generate_candidates
from submit.tracks.baxiangfenzi_agent.chemistry import canonical_smiles, is_valid_molecule, sa_score
from submit.tracks.baxiangfenzi_agent.docking import dock_smiles, prepare_receptor_pdbqt, pseudo_dock_score
from submit.tracks.baxiangfenzi_agent.retrosyn import (
    best_route_for_target,
    official_composite,
    score_molecule,
    score_route,
    try_plan_route,
    validate_route,
)
from submit.tracks.baxiangfenzi_agent.targets import binding_site_from_pdb


@dataclass
class DesignResult:
    smiles: str
    route: str
    vina_affinity: float
    sa: float
    log_lines: list[str]


def run_agent_for_target(target_pdb: Path, slot: int) -> DesignResult:
    log: list[str] = [
        f"[agent] slot={slot} phase=init target={target_pdb.name}",
        f"[agent] timestamp={datetime.now(timezone.utc).isoformat()}",
        "[agent] hypothesis=sprint3_route_enum two_stage_select vina_multimode expanded_blocks",
    ]

    site = binding_site_from_pdb(target_pdb)
    log.append(
        f"[agent] phase=analyze_target method={site.method} atoms={site.atom_count} "
        f"chains={site.chain_count} box=({site.center_x:.1f},{site.center_y:.1f},{site.center_z:.1f}) "
        f"size={site.size_x:.1f}"
    )

    max_dock = int(os.environ.get("BAXIANG_MAX_DOCK", "40"))
    select_pool = int(os.environ.get("BAXIANG_SELECT_POOL", "25"))
    composite_pool = int(os.environ.get("BAXIANG_COMPOSITE_POOL", str(max(select_pool, 40))))
    max_sa = float(os.environ.get("BAXIANG_MAX_SA", "4.0"))
    candidates = generate_candidates(target_pdb)
    log.append(
        f"[agent] phase=generate_candidates count={len(candidates)} dock_pool={max_dock} "
        f"composite_pool={composite_pool} max_sa={max_sa}"
    )

    dock_pool = candidates[:max_dock]
    ranked: list[tuple[float, str, float | None, float]] = []

    with tempfile.TemporaryDirectory(prefix="baxiang_target_") as tmp_name:
        work = Path(tmp_name)
        receptor_pdbqt = prepare_receptor_pdbqt(target_pdb, work)
        if receptor_pdbqt is None:
            log.append("[agent] phase=dock receptor_pdbqt=failed (vina/obabel missing?)")

        for idx, smi in enumerate(dock_pool):
            if not is_valid_molecule(smi):
                continue
            sa = sa_score(smi)
            if sa >= max_sa:
                continue
            affinity = dock_smiles(
                smi,
                target_pdb,
                site,
                work_dir=work,
                receptor_pdbqt=receptor_pdbqt,
            )
            pseudo = pseudo_dock_score(smi, site)
            aff_key = affinity if affinity is not None else pseudo
            if idx < 5 or idx % 10 == 0:
                log.append(
                    f"[agent] phase=dock idx={idx} affinity={aff_key:.2f} sa={sa:.2f} smiles={smi[:48]}"
                )
            ranked.append((aff_key, smi, affinity, sa))

    # More negative affinity is better
    ranked.sort(key=lambda x: x[0])

    best_smiles = None
    best_affinity = None
    best_sa = 10.0
    best_route = None
    best_composite = -1.0

    for aff_key, smi, affinity, sa in ranked[:composite_pool]:
        can = canonical_smiles(smi)
        if can is None:
            continue
        route, route_s = best_route_for_target(can)
        if not route or not validate_route(route, can):
            continue
        pseudo = pseudo_dock_score(can, site)
        mol_s = score_molecule(can, affinity, sa, pseudo)
        composite = official_composite(mol_s, route_s)
        if composite > best_composite:
            best_composite = composite
            best_smiles = can
            best_affinity = affinity
            best_sa = sa
            best_route = route
            log.append(
                f"[agent] phase=select_candidate composite={composite:.3f} "
                f"mol={mol_s:.3f} route={route_s:.3f} vina={aff_key:.2f} smiles={can[:48]}"
            )

    if best_smiles is None:
        for aff_key, smi, affinity, sa in ranked[:composite_pool]:
            can = canonical_smiles(smi) or smi
            route, route_s = best_route_for_target(can)
            if route and validate_route(route, can):
                pseudo = pseudo_dock_score(can, site)
                mol_s = score_molecule(can, affinity, sa, pseudo)
                composite = official_composite(mol_s, route_s)
                best_smiles, best_affinity, best_sa, best_route = can, affinity, sa, route
                best_composite = composite
                log.append(f"[agent] phase=select_fallback route_valid vina={aff_key:.2f} composite={composite:.3f}")
                break

    if best_smiles is None and ranked:
        for aff_key, smi, affinity, sa in ranked[:composite_pool]:
            can = canonical_smiles(smi) or smi
            route, _ = best_route_for_target(can)
            if route and validate_route(route, can):
                best_smiles, best_affinity, best_sa, best_route = can, affinity, sa, route
                log.append(f"[agent] phase=select_best_route vina={aff_key:.2f}")
                break

    if best_smiles is None and ranked:
        aff_key, smi, affinity, sa = ranked[0]
        can = canonical_smiles(smi) or smi
        best_smiles = can
        best_affinity = affinity
        best_sa = sa
        route, _ = best_route_for_target(can)
        best_route = route or try_plan_route(can)

    if best_smiles is None:
        smi = "O=C(Nc1ccccc1)c1ccccc1"
        best_smiles = smi
        best_affinity = None
        best_sa = sa_score(smi)
        route, _ = best_route_for_target(smi)
        best_route = route or try_plan_route(smi)
    elif not best_route:
        smi = "O=C(Nc1ccccc1)c1ccccc1"
        log.append(f"[agent] phase=select_default fallback=benzanilide prev={best_smiles[:32]}")
        best_smiles = smi
        best_affinity = None
        best_sa = sa_score(smi)
        route, _ = best_route_for_target(smi)
        best_route = route or try_plan_route(smi)

    if not best_route:
        from submit.pack_submission import emit_error

        emit_error("BAXIANG_ROUTE_FAILED", f"No valid route for selected molecule {best_smiles}")

    aff_out = (
        best_affinity
        if best_affinity is not None
        else pseudo_dock_score(best_smiles, site)
    )
    log.append(
        f"[agent] phase=select_best smiles={best_smiles} vina={aff_out:.2f} sa={best_sa:.2f} "
        f"composite={best_composite:.3f}"
    )
    log.append(f"[agent] phase=retrosyn route={(best_route or '')[:120]}...")
    log.append(f"[agent] phase=done slot={slot}")

    return DesignResult(
        smiles=best_smiles,
        route=best_route,
        vina_affinity=aff_out,
        sa=best_sa,
        log_lines=log,
    )
