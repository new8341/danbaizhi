"""Training hyperparameters (reference: run_high_score --score-push / --balanced)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class KSTrainConfig:
    input_steps: int = 20
    predict_steps: int = 380
    total_steps: int = 400
    model_type: str = "fno1d"
    epochs: int = 24
    batch_size: int = 16
    lr: float = 1.3e-3
    max_windows_per_sample: int = 24
    max_total_windows: int = 72000
    rollout_steps: int = 12
    rollout_weight: float = 0.38
    rollout_tail: float = 0.4
    hidden_channels: int = 52
    fno_modes: int = 14
    fno_depth: int = 3
    inference_batch_size: int = 64
    pinned_window_starts: tuple[int, ...] = (0,)


def _ks_q1(epochs: int) -> KSTrainConfig:
    """Q1-focused: wider window coverage + stronger rollout tail."""
    return KSTrainConfig(
        epochs=epochs,
        batch_size=12,
        lr=1.2e-3,
        max_windows_per_sample=36,
        max_total_windows=110000,
        rollout_steps=16,
        rollout_weight=0.44,
        rollout_tail=0.50,
        hidden_channels=56,
        fno_modes=16,
        fno_depth=4,
        pinned_window_starts=(0, 1, 2, 4, 8, 12),
    )


def _score_push(epochs: int) -> KSTrainConfig:
    return KSTrainConfig(
        epochs=epochs,
        batch_size=14,
        lr=1.25e-3,
        max_windows_per_sample=32,
        max_total_windows=100000,
        rollout_steps=14,
        rollout_weight=0.4,
        rollout_tail=0.45,
        hidden_channels=54,
        fno_modes=14,
        fno_depth=3,
        pinned_window_starts=(0, 1, 2),
    )


def _balanced(epochs: int) -> KSTrainConfig:
    return KSTrainConfig(
        epochs=epochs,
        pinned_window_starts=(0,),
    )


def load_ks_config() -> KSTrainConfig:
    if os.environ.get("SHENJING_QUICK", "").strip() in {"1", "true", "yes"}:
        return KSTrainConfig(
            epochs=3,
            max_windows_per_sample=12,
            max_total_windows=24000,
            rollout_steps=10,
            hidden_channels=48,
            fno_modes=12,
            pinned_window_starts=(0,),
        )
    epochs = int(os.environ.get("SHENJING_KS_EPOCHS", "28"))
    preset = os.environ.get("SHENJING_KS_PRESET", "ks-q1").strip().lower()
    if preset in {"ks-q1", "ks_q1", "q1"}:
        return _ks_q1(epochs)
    if preset in {"score-push", "score_push", "push"}:
        return _score_push(epochs)
    if preset in {"balanced", "default"}:
        return _balanced(epochs)
    return KSTrainConfig(epochs=epochs)
