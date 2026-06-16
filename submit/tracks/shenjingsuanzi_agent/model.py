"""FNO1d / temporal_conv next-step predictors (from champion reference)."""
from __future__ import annotations

import torch
import torch.nn.functional as F
from torch import nn


class TemporalConvPredictor(nn.Module):
    def __init__(self, input_steps: int = 10, hidden_channels: int = 64):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv1d(input_steps, hidden_channels, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_channels, hidden_channels, kernel_size=5, padding=2),
            nn.GELU(),
            nn.Conv1d(hidden_channels, 1, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return x[:, -1, :] + self.net(x)[:, 0, :]


class SpectralConv1d(nn.Module):
    def __init__(self, in_channels: int, out_channels: int, modes: int):
        super().__init__()
        self.modes = modes
        scale = 1 / (in_channels * out_channels)
        self.weight_real = nn.Parameter(scale * torch.randn(in_channels, out_channels, modes))
        self.weight_imag = nn.Parameter(scale * torch.randn(in_channels, out_channels, modes))

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x_ft = torch.fft.rfft(x, dim=-1)
        out_ft = torch.zeros(
            x.shape[0], self.weight_real.shape[1], x_ft.shape[-1],
            dtype=torch.cfloat, device=x.device,
        )
        modes = min(self.modes, x_ft.shape[-1])
        weight = torch.complex(
            self.weight_real[:, :, :modes], self.weight_imag[:, :, :modes]
        )
        out_ft[:, :, :modes] = torch.einsum("bim,iom->bom", x_ft[:, :, :modes], weight)
        return torch.fft.irfft(out_ft, n=x.shape[-1], dim=-1)


class FNO1dPredictor(nn.Module):
    def __init__(self, input_steps: int = 10, width: int = 64, modes: int = 16, depth: int = 4):
        super().__init__()
        self.input_proj = nn.Conv1d(input_steps, width, kernel_size=1)
        self.blocks = nn.ModuleList([
            nn.ModuleDict({
                "spec": SpectralConv1d(width, width, modes=modes),
                "pw": nn.Conv1d(width, width, kernel_size=1),
            })
            for _ in range(depth)
        ])
        self.out_proj = nn.Sequential(
            nn.Conv1d(width, width, kernel_size=1),
            nn.GELU(),
            nn.Conv1d(width, 1, kernel_size=1),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        last = x[:, -1, :]
        h = self.input_proj(x)
        for block in self.blocks:
            h = h + F.gelu(block["spec"](h) + block["pw"](h))
        return last + self.out_proj(h)[:, 0, :]


def build_model(
    model_type: str,
    input_steps: int,
    hidden_channels: int = 54,
    fno_modes: int = 14,
    fno_depth: int = 3,
) -> nn.Module:
    if model_type == "temporal_conv":
        return TemporalConvPredictor(input_steps=input_steps, hidden_channels=hidden_channels)
    if model_type == "fno1d":
        return FNO1dPredictor(
            input_steps=input_steps,
            width=hidden_channels,
            modes=fno_modes,
            depth=fno_depth,
        )
    raise ValueError(f"unsupported model_type={model_type!r}")
