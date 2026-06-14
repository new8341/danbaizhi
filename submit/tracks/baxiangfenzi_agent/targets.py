"""Parse target PDB and derive docking box."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class BindingSite:
    center_x: float
    center_y: float
    center_z: float
    size_x: float
    size_y: float
    size_z: float
    atom_count: int
    chain_count: int


def _parse_atoms(pdb_path: Path) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines():
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        if len(line) < 54:
            continue
        try:
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
        except ValueError:
            continue
        coords.append((x, y, z))
    return coords


def binding_site_from_pdb(pdb_path: Path, padding: float = 8.0) -> BindingSite:
    coords = _parse_atoms(pdb_path)
    if not coords:
        return BindingSite(0.0, 0.0, 0.0, 22.0, 22.0, 22.0, 0, 0)

    xs = [c[0] for c in coords]
    ys = [c[1] for c in coords]
    zs = [c[2] for c in coords]
    cx = sum(xs) / len(xs)
    cy = sum(ys) / len(ys)
    cz = sum(zs) / len(zs)
    span_x = max(xs) - min(xs) + padding
    span_y = max(ys) - min(ys) + padding
    span_z = max(zs) - min(zs) + padding
    size = max(20.0, min(28.0, span_x, span_y, span_z))
    chains = {
        line[21:22]
        for line in pdb_path.read_text(encoding="utf-8", errors="replace").splitlines()
        if line.startswith("ATOM") and len(line) > 21
    }
    return BindingSite(cx, cy, cz, size, size, size, len(coords), len(chains))
