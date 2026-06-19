"""KS equation: FNO1d train on KS_train + autoregressive predict."""
from __future__ import annotations

import time
from pathlib import Path

import torch
from torch.utils.data import DataLoader

from submit.tracks._paths import first_existing
from submit.tracks.shenjingsuanzi_agent.config import KSTrainConfig, load_ks_config
from submit.tracks.shenjingsuanzi_agent.data_utils import (
    build_field_normalizer,
    ks_baseline_from_test,
    load_3d_array,
    load_test_seed,
    sanitize_prediction,
    write_ks_prediction,
)
from submit.tracks.shenjingsuanzi_agent.engine import RolloutWindowDataset, autoregressive_predict, train_model
from submit.tracks.shenjingsuanzi_agent.model import build_model


def _test_path(problem_root: Path) -> Path | None:
    data_dir = problem_root / "data"
    return first_existing(
        data_dir / "KS_test_A.hdf5",
        data_dir / "KS_test.hdf5",
    )


def _resolve_train_path(problem_root: Path) -> Path | None:
    """Find KS_train.hdf5 on typical competition mount layouts."""
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
    for path in candidates:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        seen.add(key)
        if path.is_file():
            return path
    return None


def run_ks(problem_root: Path, out_path: Path, cfg: KSTrainConfig | None = None) -> tuple[str, list[str], float, float]:
    cfg = cfg or load_ks_config()
    logs: list[str] = []
    train_path = _resolve_train_path(problem_root) or (problem_root / "data" / "KS_train.hdf5")
    test_path = _test_path(problem_root)

    logs.append(f"[agent] ks_train_path={train_path} exists={train_path.is_file()}")
    if test_path is not None:
        logs.append(f"[agent] ks_test_path={test_path} exists=True")

    if test_path is None:
        raise FileNotFoundError(f"KS test HDF5 missing under {problem_root}/data")

    if not train_path.is_file():
        if ks_baseline_from_test(problem_root, out_path, cfg.total_steps):
            logs.append("[agent] ks_source=baseline_extrapolation (no KS_train)")
            return "baseline", logs, 0.0, 0.0
        raise FileNotFoundError(f"KS_train missing and baseline failed: {problem_root}")

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    logs.append(
        f"[agent] ks_phase=train device={device} model={cfg.model_type} "
        f"epochs={cfg.epochs} windows_cap={cfg.max_total_windows}"
    )

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
        f"[agent] ks_inference_done seconds={inference_seconds:.1f} "
        f"samples={seed.shape[0]} shape={pred.shape}"
    )
    return "fno1d_train", logs, train_seconds, inference_seconds
