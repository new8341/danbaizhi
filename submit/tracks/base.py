from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class TrackSpec:
    name: str
    task_id: str
    saisdata_hint: str
    output_name: str
    output_members: tuple[str, ...]


class TrackRunner(ABC):
    spec: TrackSpec

    @abstractmethod
    def run(self, saisdata: Path, staging_dir: Path, work_dir: Path) -> None:
        """Generate submission artifacts under staging_dir."""
