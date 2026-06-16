"""Training hyperparameters (champion reference: run_high_score score-push)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class KSTrainConfig:
    input_steps: int = 20
    predict_steps: int = 380
    total_steps: int = 400
    model_type: str = "fno1d"
    epochs: int = 10
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


def load_ks_config() -> KSTrainConfig:
    if os.environ.get("SHENJING_QUICK", "").strip() in {"1", "true", "yes"}:
        return KSTrainConfig(
            epochs=3,
            max_windows_per_sample=12,
            max_total_windows=24000,
            rollout_steps=10,
            hidden_channels=48,
            fno_modes=12,
        )
    epochs = int(os.environ.get("SHENJING_KS_EPOCHS", "10"))
    return KSTrainConfig(epochs=epochs)
