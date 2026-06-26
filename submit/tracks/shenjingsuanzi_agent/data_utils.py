"""HDF5 IO, normalization, and KS trajectory helpers."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import h5py
import numpy as np

COMMON_DATA_KEYS = ("tensor", "data", "u", "solution", "sol", "field")


def _iter_datasets(group: h5py.Group, prefix: str = "") -> list[tuple[str, h5py.Dataset]]:
    out: list[tuple[str, h5py.Dataset]] = []
    for key, value in group.items():
        path = f"{prefix}/{key}" if prefix else key
        if isinstance(value, h5py.Dataset):
            out.append((path, value))
        elif isinstance(value, h5py.Group):
            out.extend(_iter_datasets(value, path))
    return out


def load_3d_array(path: Path, preferred_key: str | None = None) -> np.ndarray:
    with h5py.File(path, "r") as f:
        datasets = _iter_datasets(f)
        if preferred_key:
            for p, ds in datasets:
                if p == preferred_key and ds.ndim == 3:
                    return ds[:].astype(np.float32)
        for key in COMMON_DATA_KEYS:
            for p, ds in datasets:
                if p.split("/")[-1].lower() == key and ds.ndim == 3:
                    return ds[:].astype(np.float32)
        for _p, ds in datasets:
            if ds.ndim == 3:
                return ds[:].astype(np.float32)
    raise ValueError(f"no 3D dataset in {path}")


@dataclass
class FieldNormalizer:
    mean: np.ndarray
    std: np.ndarray

    def normalize(self, x: np.ndarray) -> np.ndarray:
        return (x - self.mean) / self.std

    def denormalize(self, x: np.ndarray) -> np.ndarray:
        return x * self.std + self.mean


def build_field_normalizer(train: np.ndarray) -> FieldNormalizer:
    mean = train.mean(axis=(0, 1)).astype(np.float32)
    std = np.maximum(train.std(axis=(0, 1)).astype(np.float32), 1e-6)
    return FieldNormalizer(mean=mean, std=std)


def load_test_seed(path: Path, input_steps: int) -> np.ndarray:
    arr = load_3d_array(path)
    if arr.shape[1] < input_steps:
        raise ValueError(f"{path}: need >={input_steps} steps, got {arr.shape[1]}")
    return arr[:, :input_steps, :].astype(np.float32)


def sanitize_prediction(pred: np.ndarray, seed: np.ndarray, clip: float = 20.0) -> np.ndarray:
    out = np.array(pred, dtype=np.float32, copy=True)
    out[:, : seed.shape[1], :] = seed
    n, t_total, _ = out.shape
    for i in range(n):
        for t in range(seed.shape[1], t_total):
            row = out[i, t]
            if np.isfinite(row).all():
                continue
            out[i, t] = np.where(np.isfinite(row), row, out[i, t - 1])
    if clip > 0:
        out = np.clip(out, -clip, clip)
    return out


def write_ks_prediction(
    out_path: Path,
    pred: np.ndarray,
    test_path: Path,
    n_obs: int,
    n_total: int = 400,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with h5py.File(test_path, "r") as src:
        t_obs = np.asarray(src["t-coordinate"], dtype=np.float32) if "t-coordinate" in src else None
        x_coord = np.asarray(src["x-coordinate"], dtype=np.float32) if "x-coordinate" in src else None
    with h5py.File(out_path, "w") as dst:
        dst.create_dataset("tensor", data=pred.astype(np.float16), dtype=np.float16)
        if t_obs is not None and len(t_obs) == n_obs:
            dt = float(t_obs[-1] - t_obs[-2]) if n_obs > 1 else 0.5
            t_full = np.linspace(float(t_obs[0]), float(t_obs[-1]) + (n_total - n_obs) * dt, n_total)
            dst.create_dataset("t-coordinate", data=t_full.astype(np.float16))
        if x_coord is not None:
            dst.create_dataset("x-coordinate", data=x_coord.astype(np.float16))


def ks_baseline_from_test(problem_root: Path, out_path: Path, n_total: int = 400) -> bool:
    data_dir = problem_root / "data"
    for name in ("KS_test_A.hdf5", "KS_test.hdf5"):
        test_path = data_dir / name
        if test_path.is_file():
            return ks_baseline_from_test_path(test_path, out_path, n_total)
    return False


def ks_baseline_from_test_path(test_path: Path, out_path: Path, n_total: int = 400) -> bool:
    if not test_path.is_file():
        return False
    with h5py.File(test_path, "r") as src:
        obs = np.asarray(src["tensor"], dtype=np.float32)
        n_obs = obs.shape[1]
    pred = _ks_fft_damped_forecast(obs, n_total=n_total)
    pred = sanitize_prediction(pred, obs[:, :n_obs, :])
    write_ks_prediction(out_path, pred, test_path, n_obs, n_total)
    return True


def _ks_fft_damped_forecast(obs: np.ndarray, n_total: int = 400) -> np.ndarray:
    """Forecast KS by extending observed Fourier modes with damped AR(1).

    The previous safe baseline copied the final observed frame through all
    future steps.  This keeps the IC guarantee but loses the KS trajectory's
    short-term phase velocity and long-horizon distribution.  The update uses
    only mounted test observations: estimate one complex growth factor per
    sample/frequency from the first 20 steps, clamp its magnitude for stability,
    then roll forward in Fourier space.  No training data, model weights, or
    precomputed predictions are required.
    """
    obs = np.asarray(obs, dtype=np.float32)
    if obs.ndim != 3:
        raise ValueError(f"KS tensor must be 3D (N,T,X), got {obs.shape}")
    n, n_obs, n_x = obs.shape
    if n_obs < 2:
        raise ValueError(f"KS tensor needs at least two observed steps, got {n_obs}")
    if n_total < n_obs:
        raise ValueError(f"n_total={n_total} smaller than observed steps {n_obs}")

    pred = np.empty((n, n_total, n_x), dtype=np.float32)
    pred[:, :n_obs, :] = obs
    modes = np.fft.rfft(obs, axis=-1)
    prev = modes[:, :-1, :]
    nxt = modes[:, 1:, :]
    denom = np.maximum(np.sum(np.abs(prev) ** 2, axis=1), 1e-8)
    coeff = np.sum(nxt * np.conj(prev), axis=1) / denom

    magnitude = np.minimum(np.abs(coeff), 0.98)
    phase = np.angle(coeff) * 0.5
    coeff = magnitude * np.exp(1j * phase)

    current = modes[:, -1, :].copy()
    for step in range(n_obs, n_total):
        current = current * coeff
        frame = np.fft.irfft(current, n=n_x, axis=-1).real.astype(np.float32)
        if step >= 80:
            frame = 0.99 * frame + 0.005 * (
                np.roll(frame, 1, axis=-1) + np.roll(frame, -1, axis=-1)
            )
        pred[:, step, :] = frame
    pred[:, :n_obs, :] = obs
    return np.clip(pred, -20.0, 20.0)
