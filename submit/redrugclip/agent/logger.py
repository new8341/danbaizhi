"""Structured agent log for result.log (competition audit trail)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path


class AgentLog:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sections: list[str] = []

    def header(self, title: str) -> None:
        self._sections.append(f"\n{'=' * 72}\n{title}\n{'=' * 72}")

    def line(self, msg: str) -> None:
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._sections.append(f"[{ts}] {msg}")

    def block(self, text: str) -> None:
        self._sections.append(text)

    def flush(self) -> None:
        existing = ""
        if self.path.is_file():
            existing = self.path.read_text(encoding="utf-8")
        self.path.write_text(existing + "\n".join(self._sections) + "\n", encoding="utf-8")
        self._sections.clear()

    def write_full(self, content: str) -> None:
        self.path.write_text(content, encoding="utf-8")
