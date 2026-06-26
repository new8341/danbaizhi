#!/usr/bin/env python
"""对 output.zip 做本地弱评测（多样性、几何）及可选 GT 基准分近似。

由 python code/main.py eval 调用。
--zip 与 --problems-dir 相对 Project 根目录（见 _project_root()）。
不影响提交生成逻辑。
"""

from __future__ import annotations

import argparse
import json
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import numpy as np


# ---------------------------------------------------------------------------
# 路径与赛题加载
# ---------------------------------------------------------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _load_problem_seq(problems_dir: Path, problem_id: int) -> tuple[str, int]:
    path = problems_dir / f"{problem_id}.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    seq = data[0]["sequences"][0]["proteinChain"]["sequence"].strip().upper()
    return seq, len(seq)


# ---------------------------------------------------------------------------
# 结构读写（mdtraj，坐标单位 nm）
# ---------------------------------------------------------------------------
def _load_ca_nm(cif_path: Path) -> np.ndarray:
    import mdtraj as md

    t = md.load(str(cif_path))
    idx = t.topology.select("name CA")
    if len(idx) == 0:
        raise ValueError(f"No CA in {cif_path}")
    return np.asarray(t.xyz[0, idx, :], dtype=float)


def _load_heavy_atoms_nm(cif_path: Path) -> tuple[np.ndarray, np.ndarray]:
    """返回重原子坐标（nm）与残基索引。"""
    import mdtraj as md

    t = md.load(str(cif_path))
    heavy = []
    residues = []
    for atom in t.topology.atoms:
        symbol = str(atom.element.symbol).upper() if atom.element is not None else ""
        if symbol == "H":
            continue
        heavy.append(int(atom.index))
        residues.append(int(atom.residue.index))
    if not heavy:
        return np.zeros((0, 3), dtype=float), np.zeros((0,), dtype=int)
    return np.asarray(t.xyz[0, heavy, :], dtype=float), np.asarray(residues, dtype=int)


# ---------------------------------------------------------------------------
# 几何指标（RMSD、键长、碰撞代理）
# ---------------------------------------------------------------------------
def _kabsch_rmsd_angstrom(a_nm: np.ndarray, b_nm: np.ndarray) -> float:
    """Kabsch 对齐后的 RMSD（埃，相同原子数 N）。"""
    a = np.asarray(a_nm, dtype=float) * 10.0
    b = np.asarray(b_nm, dtype=float) * 10.0
    n = a.shape[0]
    if b.shape[0] != n:
        raise ValueError("Mismatched lengths for RMSD")
    a_c = a - a.mean(axis=0)
    b_c = b - b.mean(axis=0)
    h = a_c.T @ b_c
    u, _, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0.0:
        vt[-1, :] *= -1.0
        r = vt.T @ u.T
    b_fit = (r @ b_c.T).T
    return float(np.sqrt(np.mean(np.sum((a_c - b_fit) ** 2, axis=1))))


def _trim_pair(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n = min(a.shape[0], b.shape[0])
    return a[:n].copy(), b[:n].copy()


def _pairwise_rmsd_matrix(coords_list: list[np.ndarray]) -> np.ndarray:
    k = len(coords_list)
    mat = np.zeros((k, k), dtype=float)
    for i in range(k):
        for j in range(i + 1, k):
            ai, aj = _trim_pair(coords_list[i], coords_list[j])
            d = _kabsch_rmsd_angstrom(ai, aj)
            mat[i, j] = d
            mat[j, i] = d
    return mat


def _ca_spacing_stats(coords_nm: np.ndarray) -> dict[str, float]:
    """沿链的 CA-CA 间距（nm）。"""
    if coords_nm.shape[0] < 2:
        return {"mean_step_nm": 0.0, "min_step_nm": 0.0, "frac_lt_0_25nm": 0.0}
    v = np.linalg.norm(np.diff(coords_nm, axis=0), axis=1)
    return {
        "mean_step_nm": float(np.mean(v)),
        "min_step_nm": float(np.min(v)),
        "frac_lt_0_25nm": float(np.mean(v < 0.25)),
    }


def _simple_clash_frac(coords_nm: np.ndarray, min_sep_nm: float = 0.35) -> float:
    """非相邻 CA 对距离小于 min_sep_nm 的比例（粗碰撞指标）。"""
    n = coords_nm.shape[0]
    if n < 3:
        return 0.0
    bad = 0
    total = 0
    for i in range(n):
        for j in range(i + 2, n):
            d = float(np.linalg.norm(coords_nm[i] - coords_nm[j]))
            total += 1
            if d < min_sep_nm:
                bad += 1
    return float(bad / total) if total else 0.0


def _heavy_atom_clash_proxy(
    coords_nm: np.ndarray,
    residue_idx: np.ndarray,
    min_sep_nm: float = 0.20,
) -> dict[str, float]:
    """基于网格的重原子碰撞代理，排除同残基/相邻残基。"""
    n = int(coords_nm.shape[0])
    if n < 2:
        return {"frac": 0.0, "bad_pairs": 0.0, "checked_pairs": 0.0}
    cell = float(min_sep_nm)
    buckets: dict[tuple[int, int, int], list[int]] = {}
    bad = 0
    checked = 0
    for i, xyz in enumerate(coords_nm):
        key = tuple(np.floor(xyz / cell).astype(int).tolist())
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    neigh = (key[0] + dx, key[1] + dy, key[2] + dz)
                    for j in buckets.get(neigh, []):
                        if abs(int(residue_idx[i]) - int(residue_idx[j])) <= 1:
                            continue
                        checked += 1
                        if float(np.linalg.norm(coords_nm[i] - coords_nm[j])) < min_sep_nm:
                            bad += 1
        buckets.setdefault(key, []).append(i)
    return {
        "frac": float(bad / checked) if checked else 0.0,
        "bad_pairs": float(bad),
        "checked_pairs": float(checked),
    }


# ---------------------------------------------------------------------------
# 可选：与 GT 比对（基准分近似）
# ---------------------------------------------------------------------------
def _glob_gt_cifs(gt_dir: Path, problem_id: int) -> list[Path]:
    patterns = [
        f"{problem_id}_*.cif",
        f"{problem_id}_*.mmcif",
        f"p{problem_id}_*.cif",
    ]
    out: list[Path] = []
    for pat in patterns:
        out.extend(sorted(gt_dir.glob(pat)))
    seen = set()
    uniq = []
    for p in out:
        k = str(p.resolve())
        if k not in seen:
            seen.add(k)
            uniq.append(p)
    return uniq


def _base_score_from_gt(
    pred_coords: list[np.ndarray],
    gt_coords: list[np.ndarray],
) -> dict[str, float] | None:
    if not pred_coords or not gt_coords:
        return None
    cov = []
    for g in gt_coords:
        best = 1e9
        for p in pred_coords:
            gg, pp = _trim_pair(g, p)
            if gg.shape[0] < 3:
                continue
            best = min(best, _kabsch_rmsd_angstrom(pp, gg))
        cov.append(best)
    prec = []
    for p in pred_coords:
        best = 1e9
        for g in gt_coords:
            gg, pp = _trim_pair(g, p)
            if gg.shape[0] < 3:
                continue
            best = min(best, _kabsch_rmsd_angstrom(pp, gg))
        prec.append(best)
    coverage_rmsd = float(np.mean(cov)) if cov else 10.0
    precision_rmsd = float(np.mean(prec)) if prec else 10.0
    coverage_score = max(0.0, 1.0 - coverage_rmsd / 10.0)
    precision_score = max(0.0, 1.0 - precision_rmsd / 10.0)
    base_score = (coverage_score + precision_score) / 2.0
    return {
        "coverage_rmsd_angstrom": coverage_rmsd,
        "precision_rmsd_angstrom": precision_rmsd,
        "coverage_score": coverage_score,
        "precision_score": precision_score,
        "base_score_approx": base_score,
    }


# ---------------------------------------------------------------------------
# 主评测循环：解压 zip 后逐题统计
# ---------------------------------------------------------------------------
def evaluate(
    zip_path: Path,
    problems_dir: Path,
    gt_dir: Path | None,
    out_json: Path | None,
) -> dict[str, Any]:
    root = _project_root()
    zip_path = zip_path if zip_path.is_absolute() else (root / zip_path)
    problems_dir = problems_dir if problems_dir.is_absolute() else (root / problems_dir)
    if not zip_path.exists():
        raise FileNotFoundError(zip_path)

    report: dict[str, Any] = {"zip": str(zip_path), "problems": {}}

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp_path)

        for pid in (1, 2, 3):
            seq, l_seq = _load_problem_seq(problems_dir, pid)
            pred_files = sorted(tmp_path.glob(f"{pid}_conf*_pred.cif"))
            pred_coords: list[np.ndarray] = []
            for f in pred_files:
                pred_coords.append(_load_ca_nm(f))

            block: dict[str, Any] = {
                "n_conformers": len(pred_files),
                "target_sequence_length": l_seq,
                "files": [f.name for f in pred_files],
            }

            if pred_coords:
                lens = [c.shape[0] for c in pred_coords]
                block["pred_ca_lengths"] = lens
                block["length_ok"] = all(n == l_seq for n in lens)
                if len(pred_coords) >= 2:
                    mat = _pairwise_rmsd_matrix(pred_coords)
                    triu = mat[np.triu_indices_from(mat, k=1)]
                    block["pairwise_ca_rmsd_A"] = {
                        "mean": float(np.mean(triu)),
                        "std": float(np.std(triu)),
                        "max": float(np.max(triu)),
                    }
                spacing = [_ca_spacing_stats(c) for c in pred_coords]
                block["ca_spacing_nm"] = {
                    "mean_step_mean": float(np.mean([s["mean_step_nm"] for s in spacing])),
                    "frac_short_bonds_mean": float(np.mean([s["frac_lt_0_25nm"] for s in spacing])),
                }
                block["clash_proxy_mean"] = float(
                    np.mean([_simple_clash_frac(c) for c in pred_coords])
                )
                heavy_stats = []
                for f in pred_files:
                    heavy_xyz, heavy_res = _load_heavy_atoms_nm(f)
                    heavy_stats.append(_heavy_atom_clash_proxy(heavy_xyz, heavy_res))
                block["heavy_atom_clash_proxy"] = {
                    "frac_mean": float(np.mean([s["frac"] for s in heavy_stats])),
                    "bad_pairs_mean": float(np.mean([s["bad_pairs"] for s in heavy_stats])),
                    "checked_pairs_mean": float(np.mean([s["checked_pairs"] for s in heavy_stats])),
                }

            if gt_dir is not None:
                gdir = gt_dir if gt_dir.is_absolute() else (root / gt_dir)
                if gdir.exists():
                    gt_files = _glob_gt_cifs(gdir, pid)
                    gt_coords = []
                    for gf in gt_files:
                        try:
                            gt_coords.append(_load_ca_nm(gf))
                        except Exception:
                            continue
                    if gt_coords:
                        bs = _base_score_from_gt(pred_coords, gt_coords)
                        if bs:
                            block["gt_against_pred"] = bs

            report["problems"][str(pid)] = block

    if out_json:
        out_json.parent.mkdir(parents=True, exist_ok=True)
        out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


# ---------------------------------------------------------------------------
# 命令行
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="提交 zip 的本地弱评测")
    p.add_argument("--zip", default="results/submission/output.zip", help="output.zip 路径")
    p.add_argument("--problems-dir", default="document", help="含 1.json 2.json 3.json 的目录")
    p.add_argument(
        "--gt-dir",
        default="",
        help="可选：GT mmCIF 目录（如 1_*.cif），用于基准分近似",
    )
    p.add_argument(
        "--out-json",
        default="results/submission/local_eval.json",
        help="完整报告 JSON 输出路径",
    )
    return p.parse_args()


def main() -> None:
    args = parse_args()
    root = _project_root()
    gt = Path(args.gt_dir) if args.gt_dir.strip() else None
    out = Path(args.out_json)
    out = out if out.is_absolute() else (root / out)
    rep = evaluate(Path(args.zip), Path(args.problems_dir), gt, out)
    print(json.dumps(rep, ensure_ascii=False, indent=2))
    print(f"[DONE] Wrote {out}")


if __name__ == "__main__":
    main()
