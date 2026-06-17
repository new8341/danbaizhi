"""Training and autoregressive inference."""
from __future__ import annotations

import time

import numpy as np
import torch
from torch import nn
from torch.optim import AdamW
from torch.utils.data import DataLoader, Dataset


class RolloutWindowDataset(Dataset):
    def __init__(
        self,
        data: np.ndarray,
        input_steps: int,
        rollout_steps: int,
        max_windows_per_sample: int | None = None,
        max_total_windows: int | None = None,
        pinned_starts: tuple[int, ...] = (0,),
    ):
        self.data = data.astype(np.float32)
        self.input_steps = input_steps
        self.rollout_steps = rollout_steps
        self.indices: list[tuple[int, int]] = []
        n, t, _ = self.data.shape
        max_start = t - input_steps - rollout_steps
        if max_start < 0:
            raise ValueError(f"time length {t} too short")
        pinned_set = set(pinned_starts)
        for i in range(n):
            pinned = [s for s in pinned_starts if 0 <= s <= max_start]
            other = [s for s in range(max_start + 1) if s not in pinned_set]
            if max_windows_per_sample is not None:
                cap = max_windows_per_sample
                extra = max(0, cap - len(pinned))
                starts = pinned + other[:extra]
            else:
                starts = list(range(max_start + 1))
            for s in starts:
                self.indices.append((i, s))
        if max_total_windows is not None and len(self.indices) > max_total_windows:
            pinned_idx = [j for j, (_sid, start) in enumerate(self.indices) if start in pinned_set]
            other_idx = [j for j, (_sid, start) in enumerate(self.indices) if start not in pinned_set]
            rng = np.random.default_rng(42)
            keep_other = min(len(other_idx), max(0, max_total_windows - len(pinned_idx)))
            if keep_other < len(other_idx):
                pick = rng.choice(other_idx, size=keep_other, replace=False)
                other_idx = [int(x) for x in pick]
            merged = sorted(set(pinned_idx) | set(other_idx))
            if len(merged) > max_total_windows:
                merged = merged[:max_total_windows]
            self.indices = [self.indices[j] for j in merged]

    def __len__(self) -> int:
        return len(self.indices)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        sid, start = self.indices[idx]
        sample = self.data[sid]
        x = sample[start : start + self.input_steps]
        y = sample[start + self.input_steps : start + self.input_steps + self.rollout_steps]
        return torch.from_numpy(x), torch.from_numpy(y)


def _rollout_loss(model: nn.Module, x: torch.Tensor, y_roll: torch.Tensor, tail: float) -> torch.Tensor:
    k = y_roll.shape[1]
    weights = torch.linspace(1.0, 1.0 + tail, k, device=x.device, dtype=x.dtype)
    state = x
    total = torch.tensor(0.0, device=x.device, dtype=x.dtype)
    crit = nn.MSELoss()
    for step in range(k):
        pred = model(state)
        total = total + weights[step] * crit(pred, y_roll[:, step, :])
        if step + 1 < k:
            gt = y_roll[:, step, :].unsqueeze(1)
            state = torch.cat([state[:, 1:, :], gt], dim=1)
    return total / weights.sum()


def train_model(
    model: nn.Module,
    loader: DataLoader,
    epochs: int,
    lr: float,
    device: torch.device,
    rollout_weight: float = 0.38,
    rollout_tail: float = 0.42,
    weight_decay: float = 1e-4,
    grad_clip: float = 2.0,
) -> float:
    model.to(device)
    model.train()
    opt = AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, epochs))
    crit = nn.MSELoss()
    start = time.perf_counter()
    for _epoch in range(epochs):
        for x, y_roll in loader:
            x, y_roll = x.to(device), y_roll.to(device)
            opt.zero_grad()
            loss_one = crit(model(x), y_roll[:, 0, :])
            if y_roll.shape[1] > 1 and rollout_weight > 0:
                loss_roll = _rollout_loss(model, x, y_roll, rollout_tail)
                loss = (1.0 - rollout_weight) * loss_one + rollout_weight * loss_roll
            else:
                loss = loss_one
            if not torch.isfinite(loss):
                continue
            loss.backward()
            if grad_clip > 0:
                nn.utils.clip_grad_norm_(model.parameters(), grad_clip)
            opt.step()
        sched.step()
    return time.perf_counter() - start


@torch.inference_mode()
def autoregressive_predict(
    model: nn.Module,
    seed: np.ndarray,
    predict_steps: int,
    device: torch.device,
    batch_size: int = 64,
) -> np.ndarray:
    model.eval()
    model.to(device)
    n = seed.shape[0]
    out = np.empty((n, seed.shape[1] + predict_steps, seed.shape[-1]), dtype=np.float32)
    use_amp = device.type == "cuda"
    for b0 in range(0, n, batch_size):
        b1 = min(b0 + batch_size, n)
        window = torch.from_numpy(seed[b0:b1].astype(np.float32)).to(device)
        hist = window
        steps: list[torch.Tensor] = []
        ctx = torch.autocast(device_type="cuda", dtype=torch.float16, enabled=use_amp)
        with ctx:
            for _ in range(predict_steps):
                fallback = hist[:, -1, :]
                nxt = model(window)
                nxt = torch.where(torch.isfinite(nxt), nxt, fallback)
                nxt = torch.clamp(nxt, -20.0, 20.0).unsqueeze(1)
                steps.append(nxt)
                window = torch.cat([window[:, 1:, :], nxt], dim=1)
        full = torch.cat([hist] + steps, dim=1)
        out[b0:b1] = full.detach().cpu().numpy()
    return out
