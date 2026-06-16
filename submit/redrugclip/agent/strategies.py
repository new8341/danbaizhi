"""Agent strategies — tuned using platform score feedback (hybrid_max_qed ≈ 18.87)."""

from __future__ import annotations

from dataclasses import dataclass

from src.scoring import AggregateMode, ScoringConfig, get_scorer

# Known platform results (for agent diagnosis; not used for training on test labels)
PLATFORM_SCORE_HISTORY = (
    {"date": "2026-05-21 20:28:29", "score": 18.873261, "strategy": "hybrid_max_qed"},
    {"date": "2026-05-22 07:18:22", "score": 11.294361, "strategy": "ensemble_ef1_sharp"},
)


@dataclass(frozen=True)
class Strategy:
    name: str
    scorer: str
    aggregate: AggregateMode
    temperature: float
    use_qed_bonus: float
    use_drug_likeness: bool
    description: str
    substructure_bonus: float = 0.0
    physchem_bonus: float = 0.0
    pocket_heavy_bonus: float = 0.02
    fp_kinds: tuple[str, ...] = ("morgan2",)
    fp_weights: dict[str, float] | None = None
    smiles_sim_weight: float = 0.0
    rejected: bool = False  # failed on platform; agent will skip unless forced


def default_strategy_grid() -> list[Strategy]:
    """Search grid centered on proven hybrid_max_qed; exclude failed ensemble-heavy configs."""
    return [
        Strategy(
            name="hybrid_max_qed",
            scorer="hybrid",
            aggregate=AggregateMode.MAX,
            temperature=1.0,
            use_qed_bonus=0.05,
            use_drug_likeness=True,
            pocket_heavy_bonus=0.02,
            description="Champion (platform 18.87): Morgan2 vs co-crystal + QED/drug-likeness.",
        ),
        Strategy(
            name="hybrid_max_qed_v2",
            scorer="hybrid",
            aggregate=AggregateMode.MAX,
            temperature=1.0,
            use_qed_bonus=0.04,
            use_drug_likeness=True,
            pocket_heavy_bonus=0.02,
            smiles_sim_weight=0.08,
            description="Champion + light SMILES Tanimoto vs co-crystal (conservative EF1% tweak).",
        ),
        Strategy(
            name="hybrid_dual_fp",
            scorer="hybrid",
            aggregate=AggregateMode.MAX,
            temperature=1.0,
            use_qed_bonus=0.05,
            use_drug_likeness=True,
            fp_kinds=("morgan2", "fcfp"),
            fp_weights={"morgan2": 0.88, "fcfp": 0.12},
            description="90% Morgan2 + 12% FCFP blend; same QED prior as champion.",
        ),
        Strategy(
            name="baseline_fp_max",
            scorer="fingerprint",
            aggregate=AggregateMode.MAX,
            temperature=1.0,
            use_qed_bonus=0.0,
            use_drug_likeness=False,
            description="Pure Morgan2 Tanimoto baseline (reproduce).",
        ),
        Strategy(
            name="ensemble_ef1_sharp",
            scorer="ensemble",
            aggregate=AggregateMode.MAX,
            temperature=0.75,
            use_qed_bonus=0.03,
            use_drug_likeness=True,
            fp_kinds=("morgan2", "morgan3", "fcfp", "maccs"),
            physchem_bonus=0.15,
            substructure_bonus=0.08,
            pocket_heavy_bonus=0.02,
            description="FAILED platform 11.29 — kept for audit only.",
            rejected=True,
        ),
    ]


def strategy_to_config(s: Strategy) -> tuple:
    kinds = tuple(s.fp_kinds)
    weights = s.fp_weights or {k: 1.0 / len(kinds) for k in kinds}
    cfg = ScoringConfig(
        aggregate=s.aggregate,
        temperature=s.temperature,
        use_qed_bonus=s.use_qed_bonus,
        use_drug_likeness=s.use_drug_likeness,
        fp_kinds=kinds,
        fp_weights=weights,
        substructure_bonus=s.substructure_bonus,
        physchem_bonus=s.physchem_bonus,
        pocket_heavy_bonus=s.pocket_heavy_bonus,
        smiles_sim_weight=s.smiles_sim_weight,
    )
    return get_scorer(s.scorer), cfg
