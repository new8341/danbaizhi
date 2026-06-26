"""Parse target PDB and derive docking box (pocket-aware when possible)."""
from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

# Solvents, ions, buffers — not binding ligands
_SKIP_HET = frozenset(
    {
        "HOH",
        "WAT",
        "DOD",
        "SO4",
        "PO4",
        "GOL",
        "EDO",
        "ACT",
        "DMS",
        "PEG",
        "CL",
        "NA",
        "K",
        "MG",
        "ZN",
        "CA",
        "MN",
        "FE",
        "CU",
        "CD",
        "NI",
        "CO",
    }
)

_STANDARD_AA = frozenset(
    {
        "ALA",
        "ARG",
        "ASN",
        "ASP",
        "CYS",
        "GLN",
        "GLU",
        "GLY",
        "HIS",
        "ILE",
        "LEU",
        "LYS",
        "MET",
        "PHE",
        "PRO",
        "SER",
        "THR",
        "TRP",
        "TYR",
        "VAL",
        "SEC",
        "PYL",
    }
)


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
    method: str = "protein_com"


def _parse_lines(pdb_path: Path) -> list[str]:
    return pdb_path.read_text(encoding="utf-8", errors="replace").splitlines()


def _coord(line: str) -> tuple[float, float, float] | None:
    if len(line) < 54:
        return None
    try:
        return float(line[30:38]), float(line[38:46]), float(line[46:54])
    except ValueError:
        return None


def _ligand_coords(lines: list[str]) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for line in lines:
        if not line.startswith("HETATM"):
            continue
        resn = line[17:20].strip().upper()
        if resn in _SKIP_HET or resn in _STANDARD_AA:
            continue
        c = _coord(line)
        if c is not None:
            coords.append(c)
    return coords


def _ca_coords(lines: list[str]) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for line in lines:
        if not line.startswith("ATOM"):
            continue
        if len(line) > 12 and line[12:16].strip() != "CA":
            continue
        c = _coord(line)
        if c is not None:
            coords.append(c)
    return coords


def _all_heavy_coords(lines: list[str]) -> list[tuple[float, float, float]]:
    coords: list[tuple[float, float, float]] = []
    for line in lines:
        if not (line.startswith("ATOM") or line.startswith("HETATM")):
            continue
        c = _coord(line)
        if c is not None:
            coords.append(c)
    return coords


def _centroid(coords: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    n = len(coords)
    return (
        sum(c[0] for c in coords) / n,
        sum(c[1] for c in coords) / n,
        sum(c[2] for c in coords) / n,
    )


def _dist(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2 + (a[2] - b[2]) ** 2)


def _dense_ca_pocket(cas: list[tuple[float, float, float]]) -> tuple[float, float, float]:
    """CA with most neighbors within 10 Å — proxy for buried pocket."""
    if not cas:
        return 0.0, 0.0, 0.0
    best = cas[0]
    best_n = -1
    for c in cas:
        n = sum(1 for o in cas if _dist(c, o) < 10.0)
        if n > best_n:
            best_n = n
            best = c
    return best


def _box_size(coords: list[tuple[float, float, float]], center: tuple[float, float, float]) -> float:
    if not coords:
        return 22.0
    max_span = 0.0
    for c in coords:
        max_span = max(max_span, _dist(c, center))
    # Tight pocket box 18–24 Å
    return max(18.0, min(24.0, max_span * 2.0 + 6.0))


def binding_site_from_pdb(pdb_path: Path, padding: float = 8.0) -> BindingSite:
    lines = _parse_lines(pdb_path)
    all_coords = _all_heavy_coords(lines)
    ligand = _ligand_coords(lines)
    cas = _ca_coords(lines)

    chains = {
        line[21:22]
        for line in lines
        if line.startswith("ATOM") and len(line) > 21
    }

    if ligand:
        center = _centroid(ligand)
        size = _box_size(ligand, center)
        method = "ligand_hetatm"
    elif cas:
        center = _dense_ca_pocket(cas)
        nearby = [c for c in all_coords if _dist(c, center) < 14.0]
        size = _box_size(nearby or cas, center)
        method = "ca_density"
    elif all_coords:
        center = _centroid(all_coords)
        xs = [c[0] for c in all_coords]
        ys = [c[1] for c in all_coords]
        zs = [c[2] for c in all_coords]
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)) + padding
        size = max(20.0, min(28.0, span))
        method = "protein_com"
    else:
        return BindingSite(0.0, 0.0, 0.0, 22.0, 22.0, 22.0, 0, 0, "empty")

    return BindingSite(
        center[0],
        center[1],
        center[2],
        size,
        size,
        size,
        len(all_coords),
        len(chains),
        method,
    )
