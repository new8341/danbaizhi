"""EF1% metric for proxy validation (external labeled data only — not competition test)."""

from __future__ import annotations

import csv
from pathlib import Path


def enrichment_factor_at_fraction(
    scores: list[tuple[str, float, int]],
    fraction: float = 0.01,
) -> float:
    """
    scores: list of (id, score, label) where label 1=active, 0=inactive/decoy.
    Higher score = predicted active.
    """
    if not scores:
        return 0.0
    n = len(scores)
    k = max(1, int(n * fraction))
    ranked = sorted(scores, key=lambda x: x[1], reverse=True)
    top = ranked[:k]
    actives_total = sum(s[2] for s in scores)
    if actives_total == 0:
        return 0.0
    actives_top = sum(s[2] for s in top)
    expected_random = actives_total * (k / n)
    if expected_random <= 0:
        return 0.0
    return actives_top / expected_random


def load_labeled_tsv(path: Path) -> list[tuple[str, int]]:
    """TSV: ligand_id \\t label (0/1) or smiles \\t label."""
    rows: list[tuple[str, int]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            parts = line.strip().split("\t")
            if len(parts) < 2:
                continue
            rows.append((parts[0], int(parts[1])))
    return rows


def mean_ef1_from_submission(
    score_by_id: dict[str, float],
    labels: dict[str, int],
    fraction: float = 0.01,
) -> float:
    scores = [
        (lid, score_by_id[lid], labels[lid])
        for lid in labels
        if lid in score_by_id
    ]
    return enrichment_factor_at_fraction(scores, fraction)


def write_proxy_template(path: Path) -> None:
    """Placeholder for user-provided external validation labels."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Optional proxy validation: ligand_id\\tlabel (1=active,0=decoy)\n",
        encoding="utf-8",
    )
