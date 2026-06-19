"""KS equation: FNO1d train on KS_train + autoregressive predict."""
from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import torch
from torch import nn
from torch.utils.data import DataLoader

from submit.tracks._paths import first_existing
from submit.tracks.shenjingsuanzi_agent.config import KSTrainConfig, load_ks_config
from submit.tracks.shenjingsuanzi_agent.data_utils import (
    FieldNormalizer,
    build_field_normalizer,
    ks_baseline_from_test_path,
    load_3d_array,
    load_test_seed,
    sanitize_prediction,
    write_ks_prediction,
)
from submit.tracks.shenjingsuanzi_agent.engine import RolloutWindowDataset, autoregressive_predict, train_model
from submit.tracks.shenjingsuanzi_agent.model import build_model


@dataclass
class KsRunState:
    model: nn.Module
    normalizer: FieldNormalizer
    cfg: KSTrainConfig
    train_seconds: float
    source: str


def resolve_ks_test_path(saisdata: Path, problem_root: Path, board: str) -> Path | None:
    """A: problem1/data/KS_test_A.hdf5; B: /saisdata/66/KS_test_B.hdf5 or problem1/data/."""
    board = board.upper()
    if board == "A":
        return first_existing(
            problem_root / "data" / "KS_test_A.hdf5",
            problem_root / "data" / "KS_test.hdf5",
        )
    return first_existing(
        saisdata / "66" / "KS_test_B.hdf5",
        problem_root / "data" / "KS_test_B.hdf5",
        saisdata / "KS_test_B.hdf5",
    )


def list_ks_train_candidates(problem_root: Path) -> list[tuple[Path, bool]]:
    """All candidate KS_train paths with existence flags (for agent logging)."""
    sais = problem_root
    for _ in range(4):
        sais = sais.parent
    candidates = [
        problem_root / "data" / "KS_train.hdf5",
        sais / "48" / "KS_train.hdf5",
        sais / "48" / "problem1" / "data" / "KS_train.hdf5",
        sais / "48" / "data" / "KS_train.hdf5",
    ]
    seen: set[str] = set()
    out: list[tuple[Path, bool]] = []
    for path in candidates:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        out.append((path, path.is_file()))
    return out


def _resolve_train_path(problem_root: Path) -> Path | None:
    for path, exists in list_ks_train_candidates(problem_root):
        if exists:
            return path
    return None


def _train_ks(
    train_path: Path,
    cfg: KSTrainConfig,
    device: torch.device,
) -> tuple[nn.Module, FieldNormalizer, float, list[str]]:
    logs: list[str] = []
    train_arr = load_3d_array(train_path)
    logs.append(f"[agent] ks_train_shape={tuple(train_arr.shape)}")
    normalizer = build_field_normalizer(train_arr)
    train_norm = normalizer.normalize(train_arr)
    ds = RolloutWindowDataset(
        train_norm,
        input_steps=cfg.input_steps,
        rollout_steps=cfg.rollout_steps,
        max_windows_per_sample=cfg.max_windows_per_sample,
        max_total_windows=cfg.max_total_windows,
        pinned_starts=cfg.pinned_window_starts,
    )
    loader = DataLoader(ds, batch_size=cfg.batch_size, shuffle=True, drop_last=False)
    model = build_model(
        cfg.model_type,
        input_steps=cfg.input_steps,
        hidden_channels=cfg.hidden_channels,
        fno_modes=cfg.fno_modes,
        fno_depth=cfg.fno_depth,
    )
    train_seconds = train_model(
        model,
        loader,
        epochs=cfg.epochs,
        lr=cfg.lr,
        device=device,
        rollout_weight=cfg.rollout_weight,
        rollout_tail=cfg.rollout_tail,
    )
    logs.append(f"[agent] ks_train_done seconds={train_seconds:.1f} windows={len(ds)}")
    return model, normalizer, train_seconds, logs


def _infer_ks(
    model: nn.Module,
    normalizer: FieldNormalizer,
    test_path: Path,
    out_path: Path,
    cfg: KSTrainConfig,
    device: torch.device,
) -> tuple[list[str], float]:
    logs: list[str] = []
    seed = load_test_seed(test_path, cfg.input_steps)
    seed_norm = normalizer.normalize(seed)
    inf_start = time.perf_counter()
    pred_norm = autoregressive_predict(
        model,
        seed_norm,
        predict_steps=cfg.predict_steps,
        device=device,
        batch_size=cfg.inference_batch_size,
    )
    inference_seconds = time.perf_counter() - inf_start
    pred = sanitize_prediction(normalizer.denormalize(pred_norm), seed)
    write_ks_prediction(out_path, pred, test_path, cfg.input_steps, cfg.total_steps)
    logs.append(
        f"[agent] ks_inference_done test={test_path.name} seconds={inference_seconds:.1f} "
        f"samples={seed.shape[0]} shape={pred.shape}"
    )
    return logs, inference_seconds


def run_ks(
    problem_root: Path,
    test_path: Path,
    out_path: Path,
    cfg: KSTrainConfig | None = None,
    *,
    state: KsRunState | None = None,
) -> tuple[str, list[str], float, float, KsRunState | None]:
    """Train once (first board), reuse model for additional boards."""
    cfg = cfg or load_ks_config()
    logs: list[str] = []
    logs.append(f"[agent] ks_test_path={test_path} exists={test_path.is_file()}")

    if not test_path.is_file():
        raise FileNotFoundError(f"KS test missing: {test_path}")

    if state is not None:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        state.model.to(device)
        inf_logs, inf_t = _infer_ks(state.model, state.normalizer, test_path, out_path, cfg, device)
        logs.extend(inf_logs)
        return state.source, logs, 0.0, inf_t, state

    train_path = _resolve_train_path(problem_root) or (problem_root / "data" / "KS_train.hdf5")
    for cand, exists in list_ks_train_candidates(problem_root):
        logs.append(f"[agent] ks_train_candidate path={cand} exists={exists}")
    logs.append(f"[agent] ks_train_path={train_path} exists={train_path.is_file()}")

    if not train_path.is_file():
        if ks_baseline_from_test_path(test_path, out_path, cfg.total_steps):
            logs.append("[agent] ks_source=baseline_extrapolation (no KS_train)")
            return "baseline", logs, 0.0, 0.0, None
        raise FileNotFoundError(f"KS_train missing and baseline failed: {problem_root}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logs.append(
        f"[agent] ks_phase=train device={device} model={cfg.model_type} "
        f"epochs={cfg.epochs} windows_cap={cfg.max_total_windows}"
    )
    model, normalizer, train_seconds, train_logs = _train_ks(train_path, cfg, device)
    logs.extend(train_logs)
    inf_logs, inf_t = _infer_ks(model, normalizer, test_path, out_path, cfg, device)
    logs.extend(inf_logs)
    new_state = KsRunState(
        model=model, normalizer=normalizer, cfg=cfg, train_seconds=train_seconds, source="fno1d_train"
    )
    return "fno1d_train", logs, train_seconds, inf_t, new_state
