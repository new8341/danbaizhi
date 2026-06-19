"""AutoDock Vina docking wrapper."""
from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from rdkit import Chem
from rdkit.Chem import AllChem

from submit.tracks.baxiangfenzi_agent.targets import BindingSite


def _which(cmd: str) -> str | None:
    return shutil.which(cmd)


def prepare_receptor_pdbqt(receptor_pdb: Path, cache_dir: Path) -> Path | None:
    """Build or reuse receptor PDBQT (once per target per run)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(receptor_pdb.read_bytes()).hexdigest()[:16]
    out_path = cache_dir / f"receptor_{digest}.pdbqt"
    if out_path.is_file() and out_path.stat().st_size > 0:
        return out_path
    if _prepare_receptor_pdbqt(receptor_pdb, out_path):
        return out_path
    return None


def _prepare_ligand_pdbqt(smiles: str, out_path: Path) -> bool:
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 0xC0FFEE
    if AllChem.EmbedMolecule(mol, params) != 0:
        if AllChem.EmbedMolecule(mol, randomSeed=42) != 0:
            return False
    try:
        AllChem.MMFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        pass

    mol_block = Chem.MolToMolBlock(mol)
    mol_path = out_path.with_suffix(".mol")
    pdb_path = out_path.with_suffix(".pdb")
    mol_path.write_text(mol_block, encoding="utf-8")

    obabel = _which("obabel")
    if obabel:
        subprocess.run(
            [obabel, str(mol_path), "-O", str(out_path), "--gen3d"],
            check=False,
            capture_output=True,
            text=True,
        )
        if out_path.is_file():
            return True
        subprocess.run(
            [obabel, str(mol_path), "-O", str(pdb_path), "--gen3d"],
            check=False,
            capture_output=True,
            text=True,
        )
        if pdb_path.is_file():
            subprocess.run(
                [obabel, str(pdb_path), "-O", str(out_path)],
                check=False,
                capture_output=True,
                text=True,
            )
            return out_path.is_file()
    return False


def _prepare_receptor_pdbqt(pdb_path: Path, out_path: Path) -> bool:
    obabel = _which("obabel")
    if not obabel:
        return False
    subprocess.run(
        [obabel, str(pdb_path), "-O", str(out_path), "-xr"],
        check=False,
        capture_output=True,
        text=True,
    )
    return out_path.is_file() and out_path.stat().st_size > 0


def _parse_vina_affinity(stdout: str) -> float | None:
    for line in stdout.splitlines():
        if "REMARK VINA RESULT" in line or line.strip().startswith("1 "):
            parts = line.split()
            for token in parts:
                try:
                    val = float(token)
                    if val < 0:
                        return val
                except ValueError:
                    continue
    m = re.search(r"^\s*1\s+(-?\d+\.\d+)", stdout, re.MULTILINE)
    if m:
        return float(m.group(1))
    return None


def _parse_vina_best_affinity(stdout: str) -> float | None:
    """Return best (most negative) affinity across all reported modes."""
    vals: list[float] = []
    for m in re.finditer(r"^\s*\d+\s+(-?\d+\.\d+)", stdout, re.MULTILINE):
        val = float(m.group(1))
        if val < 0:
            vals.append(val)
    return min(vals) if vals else _parse_vina_affinity(stdout)


def dock_smiles(
    smiles: str,
    receptor_pdb: Path,
    site: BindingSite,
    work_dir: Path | None = None,
    receptor_pdbqt: Path | None = None,
) -> float | None:
    """Return Vina affinity (kcal/mol, more negative is better) or None."""
    vina = _which("vina") or _which("autodock_vina")
    if not vina:
        return None

    exhaustiveness = int(os.environ.get("BAXIANG_VINA_EXHAUSTIVENESS", "6"))
    num_modes = int(os.environ.get("BAXIANG_VINA_NUM_MODES", "3"))
    tmp_ctx = tempfile.TemporaryDirectory(prefix="baxiang_dock_")
    tmp = Path(work_dir) if work_dir else Path(tmp_ctx.name)

    rec_pdbqt = receptor_pdbqt
    if rec_pdbqt is None:
        rec_pdbqt = tmp / "receptor.pdbqt"
        if not _prepare_receptor_pdbqt(receptor_pdb, rec_pdbqt):
            return None

    ligand_pdbqt = tmp / "ligand.pdbqt"
    out_pdbqt = tmp / "out.pdbqt"

    if not _prepare_ligand_pdbqt(smiles, ligand_pdbqt):
        return None

    cmd = [
        vina,
        "--receptor",
        str(rec_pdbqt),
        "--ligand",
        str(ligand_pdbqt),
        "--center_x",
        str(site.center_x),
        "--center_y",
        str(site.center_y),
        "--center_z",
        str(site.center_z),
        "--size_x",
        str(site.size_x),
        "--size_y",
        str(site.size_y),
        "--size_z",
        str(site.size_z),
        "--exhaustiveness",
        str(exhaustiveness),
        "--num_modes",
        str(num_modes),
        "--out",
        str(out_pdbqt),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    affinity = _parse_vina_best_affinity(proc.stdout + "\n" + proc.stderr)
    if work_dir is None:
        tmp_ctx.cleanup()
    return affinity


def pseudo_dock_score(smiles: str, site: BindingSite) -> float:
    """Fallback when Vina unavailable: proxy from complexity + size."""
    from rdkit.Chem import Descriptors

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0.0
    mw = Descriptors.MolWt(mol)
    return -5.0 - min(4.0, mw / 120.0) - site.atom_count * 1e-5
