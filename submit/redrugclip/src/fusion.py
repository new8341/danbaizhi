"""Fuse multiple submission CSVs via reciprocal rank fusion (RRF)."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path


def load_scores(path: Path) -> dict[tuple[str, str], float]:
    out: dict[tuple[str, str], float] = {}
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[(row["task_id"], row["ligand_id"])] = float(row["score"])
    return out


def reciprocal_rank_fusion(
    score_maps: list[dict[tuple[str, str], float]],
    weights: list[float] | None = None,
    k: int = 60,
) -> dict[tuple[str, str], float]:
    if not score_maps:
        raise ValueError("need at least one score map")
    weights = weights or [1.0] * len(score_maps)
    if len(weights) != len(score_maps):
        raise ValueError("weights length must match score_maps")

    keys = set(score_maps[0])
    for m in score_maps[1:]:
        keys &= set(m)
    if not keys:
        raise ValueError("no common (task_id, ligand_id) keys")

    by_task: dict[str, list[tuple[str, float]]] = defaultdict(list)
    for task_id, ligand_id in keys:
        by_task[task_id].append((ligand_id, score_maps[0][(task_id, ligand_id)]))

    fused: dict[tuple[str, str], float] = {}
    for task_id, items in by_task.items():
        ligand_ids = [x[0] for x in items]
        rrf = {lid: 0.0 for lid in ligand_ids}
        for w, smap in zip(weights, score_maps):
            ranked = sorted(
                ligand_ids,
                key=lambda lid: smap[(task_id, lid)],
                reverse=True,
            )
            for rank, lid in enumerate(ranked, start=1):
                rrf[lid] += w / (k + rank)
        for lid, score in rrf.items():
            fused[(task_id, lid)] = score
    return fused


def write_fused_csv(fused: dict[tuple[str, str], float], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["task_id", "ligand_id", "score"])
        for (tid, lid) in sorted(fused.keys()):
            w.writerow([tid, lid, f"{fused[(tid, lid)]:.8f}"])
