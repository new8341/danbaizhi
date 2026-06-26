"""Load ACR registry settings for multi-track docker builds."""
from __future__ import annotations

import os
from pathlib import Path

DEFAULT_REGISTRY = "crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com"
DEFAULT_NAMESPACE = "ai4s-lee"
DEFAULT_TAG = "0.1"

TRACKS = ("danbaizhi", "drugclip", "baxiangfenzi", "shenjingsuanzi")

_ENV_PATH = Path(__file__).resolve().parent / "registry.env"


def load_registry_env(env_path: Path | None = None) -> dict[str, str]:
    path = env_path or _ENV_PATH
    values = {
        "REGISTRY": os.environ.get("ACR_REGISTRY", DEFAULT_REGISTRY),
        "NAMESPACE": os.environ.get("ACR_NAMESPACE", DEFAULT_NAMESPACE),
        "TAG": os.environ.get("ACR_TAG", DEFAULT_TAG),
    }
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            if key in values and val:
                values[key] = val
    return values


def image_ref(track: str, tag: str | None = None, namespace: str | None = None, registry: str | None = None) -> str:
    cfg = load_registry_env()
    track_key = track.strip().lower()
    if track_key not in TRACKS:
        raise ValueError(f"Unknown track {track!r}; expected one of {TRACKS}")
    reg = registry or cfg["REGISTRY"]
    ns = namespace or cfg["NAMESPACE"]
    tg = tag or cfg["TAG"]
    return f"{reg}/{ns}/{track_key}:{tg}"
