"""Read per-track LLM API settings from environment (semifinal compliance)."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class LlmConfig:
    api_key: str
    base_url: str
    model: str

    @property
    def configured(self) -> bool:
        return bool(self.api_key)


def load_llm_config(prefix: str) -> LlmConfig:
    """prefix e.g. BAXIANG, DANBAIZHI, DRUGCLIP, SHENJING."""
    return LlmConfig(
        api_key=os.environ.get(f"{prefix}_LLM_API_KEY", "").strip(),
        base_url=os.environ.get(f"{prefix}_LLM_BASE_URL", "https://api.openai.com/v1").strip(),
        model=os.environ.get(f"{prefix}_LLM_MODEL", "gpt-4o-mini").strip(),
    )


def append_llm_log(lines: list[str], prefix: str, *, optional: bool = False) -> LlmConfig:
    cfg = load_llm_config(prefix)
    if cfg.configured:
        lines.append(
            f"[agent] llm=ready provider=openai_compatible base_url={cfg.base_url} model={cfg.model}"
        )
    elif optional:
        lines.append("[agent] llm=skipped (optional for this track)")
    else:
        lines.append("[agent] llm=env_missing (set *_LLM_API_KEY at image build or runtime)")
    return cfg
