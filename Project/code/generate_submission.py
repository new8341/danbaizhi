#!/usr/bin/env python
"""生成赛题提交用 mmCIF 与 output.zip。

入口：由 code/main.py predict 调用；--sources-config 内路径相对 Project 根目录（code/ 的上一级）。

每题策略（submission_sources.json）：
- template_align：NW 对齐 + 可选 diversity_filter + hybrid 全原子侧链
- template_cif：mdtraj 全原子导出 + 小角度刚体扰动（seed）
- trajectory_ca / baseline_ca：无模板/轨迹时的回退
- auto：先轨迹，再模板分支，最后 baseline_ca

随机种子 --seed（默认 42）控制扰动与多样性子采样。
"""

from __future__ import annotations

import argparse
import json
import math
import random
import re
import shutil
import subprocess
import sys
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

# ===========================================================================
# 常量：zip 成员过滤、题目模型、agent.log 审核标题
# ===========================================================================
# 仅以下文件名打入 output.zip（另含 agent.log）；调试 CIF 不打包
_SUBMISSION_CIF_RE = re.compile(r"^\d+_conf\d+_pred\.cif$")


@dataclass(frozen=True)
class Problem:
    problem_id: int
    name: str
    sequence: str
    conformer_count: int


# 写入 agent.log 的论文/报告审核标题（见 readme §11.10）
_AGENT_LOG_STAGE5_HEADING = (
    "Stage 5 - Paper and technical report (per document/rull.md audit trail):"
)
_AGENT_LOG_STAGE6_HEADING = (
    "Stage 6 - Optional future HTTP adapter (not required by document/rull.md):"
)


def validate_agent_log_paper_readiness(log_text: str) -> dict[str, Any]:
    """检查 agent.log 是否含论文/报告审核标题（离线，无 HTTP）。

    失败时返回 ``{"success": false, "error": {"code", "message", "requestId"}}``；
    此处 requestId 为空（若封装 HTTP 见 readme §11.10）。
    """
    missing: list[str] = []
    if _AGENT_LOG_STAGE5_HEADING not in log_text:
        missing.append(_AGENT_LOG_STAGE5_HEADING)
    if _AGENT_LOG_STAGE6_HEADING not in log_text:
        missing.append(_AGENT_LOG_STAGE6_HEADING)
    if missing:
        return {
            "success": False,
            "error": {
                "code": "AGENT_LOG_PAPER_SECTIONS_MISSING",
                "message": "Missing required log headings: " + " | ".join(missing),
                "requestId": "",
            },
        }
    return {"success": True}


# ===========================================================================
# 一字母氨基酸 -> PDB 三字母码（mmCIF _atom_site）
# ===========================================================================
AA3 = {
    "A": "ALA",
    "R": "ARG",
    "N": "ASN",
    "D": "ASP",
    "C": "CYS",
    "Q": "GLN",
    "E": "GLU",
    "G": "GLY",
    "H": "HIS",
    "I": "ILE",
    "L": "LEU",
    "K": "LYS",
    "M": "MET",
    "F": "PHE",
    "P": "PRO",
    "S": "SER",
    "T": "THR",
    "W": "TRP",
    "Y": "TYR",
    "V": "VAL",
}


# ===========================================================================
# 赛题 JSON 读写（data/{1,2,3}.json）
# ===========================================================================
def _load_problem(json_path: Path, problem_id: int) -> Problem:
    payload = json.loads(json_path.read_text(encoding="utf-8"))
    if not payload or not isinstance(payload, list):
        raise ValueError(f"Invalid problem json: {json_path}")
    first = payload[0]
    seq = first["sequences"][0]["proteinChain"]["sequence"].strip().upper()
    conf = int(first.get("conformer_count", 1))
    conf = max(1, min(conf, 10))
    name = str(first.get("name", f"r{problem_id:03d}"))
    return Problem(problem_id=problem_id, name=name, sequence=seq, conformer_count=conf)


# ===========================================================================
# baseline_ca：无模板/轨迹时的合成 CA 轨迹
# ===========================================================================
def _build_ca_coordinates(seq: str, conf_idx: int, seed: int) -> list[tuple[float, float, float]]:
    """生成较平滑的 CA 轨迹（基线，用于流程校验）。"""
    rng = random.Random(seed + conf_idx * 97)
    coords: list[tuple[float, float, float]] = []
    radius = 8.0 + 0.4 * conf_idx
    pitch = 1.5 + 0.05 * conf_idx
    for i in range(len(seq)):
        t = i * 0.45
        x = radius * math.cos(t) + 0.7 * math.sin(i * 0.11 + conf_idx)
        y = radius * math.sin(t) + 0.7 * math.cos(i * 0.13 + conf_idx)
        z = pitch * i + 0.8 * math.sin(i * 0.07 + conf_idx)
        # 小幅平滑噪声
        x += 0.25 * (rng.random() - 0.5)
        y += 0.25 * (rng.random() - 0.5)
        z += 0.25 * (rng.random() - 0.5)
        coords.append((x, y, z))
    return coords


# ===========================================================================
# trajectory_ca：OpenMM traj.dcd 帧聚类（可选分支）
# ===========================================================================
def _extract_ca_from_trajectory(
    traj_path: Path,
    top_path: Path,
    n_conformers: int,
) -> tuple[list[str], list[list[tuple[float, float, float]]]]:
    try:
        import mdtraj as md
        from sklearn.cluster import KMeans
    except ImportError as exc:
        raise RuntimeError(
            "mdtraj and scikit-learn are required for trajectory strategy."
        ) from exc

    traj = md.load(str(traj_path), top=str(top_path))
    ca_indices = traj.topology.select("name CA")
    if len(ca_indices) == 0:
        raise RuntimeError("No CA atoms found in trajectory topology.")

    residues = [a.residue.code if a.residue.code else "X" for a in traj.topology.atoms if a.index in ca_indices]
    X = traj.xyz[:, ca_indices, :].reshape(traj.n_frames, -1)
    k = min(max(1, n_conformers), traj.n_frames)
    model = KMeans(n_clusters=k, n_init=10, random_state=42)
    labels = model.fit_predict(X)

    frame_indices = []
    for i in range(k):
        idxs = [j for j, lb in enumerate(labels) if lb == i]
        if not idxs:
            continue
        center = model.cluster_centers_[i]
        nearest = min(idxs, key=lambda j: float(((X[j] - center) ** 2).sum()))
        frame_indices.append(nearest)

    coords_list: list[list[tuple[float, float, float]]] = []
    for fi in frame_indices:
        # mdtraj 坐标为 nm，写出 CIF 时转为埃
        c = traj.xyz[fi, ca_indices, :] * 10.0
        coords_list.append([(float(v[0]), float(v[1]), float(v[2])) for v in c])
    return residues, coords_list


# ===========================================================================
# mdtraj：加载模板（PDB/mmCIF）、选链、提取 CA
# ===========================================================================
def _pick_best_chain_index(top: Any, target_len_hint: int | None) -> int:
    """选取 CA 数最接近 target_len_hint 的蛋白链（无 hint 时取最长链）。"""
    best_ci = 0
    best_score = float("inf")
    found = False
    for ci in range(top.n_chains):
        sel = top.select(f"name CA and chainid {ci}")
        n = len(sel)
        if n == 0:
            continue
        found = True
        if target_len_hint is None:
            score = -float(n)
        else:
            score = abs(float(n - target_len_hint))
        if score < best_score:
            best_score = score
            best_ci = ci
    if not found:
        return 0
    return best_ci


def _load_single_chain_protein_traj(cif_path: Path, target_len_hint: int | None = None) -> Any:
    """加载结构并保留一条蛋白链（多链时选与目标长度最匹配者）。"""
    try:
        import mdtraj as md
    except ImportError as exc:
        raise RuntimeError("mdtraj is required for template_cif strategy.") from exc
    traj = md.load(str(cif_path))
    if traj.n_frames < 1:
        raise RuntimeError(f"Empty trajectory: {cif_path}")
    ci = _pick_best_chain_index(traj.topology, target_len_hint)
    idx = traj.topology.select(f"protein and chainid {ci}")
    if len(idx) == 0:
        idx = traj.topology.select(f"chainid {ci}")
    if len(idx) == 0:
        raise RuntimeError(f"No atoms for selected chain in {cif_path}")
    return traj.atom_slice(idx, inplace=False)


def _extract_ca_from_cif(
    cif_path: Path, target_len_hint: int | None = None
) -> tuple[list[str], list[tuple[float, float, float]]]:
    try:
        import mdtraj as md  # noqa: F401
    except ImportError as exc:
        raise RuntimeError("mdtraj is required for template_cif strategy.") from exc
    traj = _load_single_chain_protein_traj(cif_path, target_len_hint)
    ca_indices = traj.topology.select("name CA")
    if len(ca_indices) == 0:
        raise RuntimeError(f"No CA atoms found in CIF: {cif_path}")
    residues = [
        (a.residue.code if a.residue.code else "G")
        for a in traj.topology.atoms
        if a.index in ca_indices
    ]
    coords_nm = traj.xyz[0, ca_indices, :]
    coords = [(float(v[0] * 10.0), float(v[1] * 10.0), float(v[2] * 10.0)) for v in coords_nm]
    return residues, coords


# ===========================================================================
# 序列比对（Needleman-Wunsch）与 CA 坐标插值
# ===========================================================================
def _needleman_wunsch(a: str, b: str) -> tuple[str, str]:
    """全局比对（简单打分）。"""
    n, m = len(a), len(b)
    match, mismatch, gap = 2, -1, -2
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    bt = [[0] * (m + 1) for _ in range(n + 1)]  # 0 diag, 1 up, 2 left

    for i in range(1, n + 1):
        dp[i][0] = i * gap
        bt[i][0] = 1
    for j in range(1, m + 1):
        dp[0][j] = j * gap
        bt[0][j] = 2

    for i in range(1, n + 1):
        ai = a[i - 1]
        for j in range(1, m + 1):
            bj = b[j - 1]
            s_diag = dp[i - 1][j - 1] + (match if ai == bj else mismatch)
            s_up = dp[i - 1][j] + gap
            s_left = dp[i][j - 1] + gap
            best = s_diag
            move = 0
            if s_up > best:
                best = s_up
                move = 1
            if s_left > best:
                best = s_left
                move = 2
            dp[i][j] = best
            bt[i][j] = move

    i, j = n, m
    aa: list[str] = []
    bb: list[str] = []
    while i > 0 or j > 0:
        move = bt[i][j]
        if i > 0 and j > 0 and move == 0:
            aa.append(a[i - 1])
            bb.append(b[j - 1])
            i -= 1
            j -= 1
        elif i > 0 and move == 1:
            aa.append(a[i - 1])
            bb.append("-")
            i -= 1
        else:
            aa.append("-")
            bb.append(b[j - 1])
            j -= 1
    return "".join(reversed(aa)), "".join(reversed(bb))


def _interpolate_missing_coords(mapped: list[tuple[float, float, float] | None]) -> list[tuple[float, float, float]]:
    n = len(mapped)
    if n == 0:
        return []

    known = [i for i, v in enumerate(mapped) if v is not None]
    if not known:
        return [(0.0, 0.0, float(i) * 3.8) for i in range(n)]

    out = list(mapped)
    # 填充 N 端缺失
    first = known[0]
    first_v = out[first]
    assert first_v is not None
    for i in range(first - 1, -1, -1):
        out[i] = (first_v[0], first_v[1], first_v[2] - 3.8 * (first - i))
    # 填充 C 端缺失
    last = known[-1]
    last_v = out[last]
    assert last_v is not None
    for i in range(last + 1, n):
        out[i] = (last_v[0], last_v[1], last_v[2] + 3.8 * (i - last))
    # 内部缺口线性插值
    for l, r in zip(known[:-1], known[1:]):
        lv = out[l]
        rv = out[r]
        assert lv is not None and rv is not None
        gap = r - l
        if gap <= 1:
            continue
        for k in range(1, gap):
            t = k / gap
            out[l + k] = (
                lv[0] * (1 - t) + rv[0] * t,
                lv[1] * (1 - t) + rv[1] * t,
                lv[2] * (1 - t) + rv[2] * t,
            )
    return [v if v is not None else (0.0, 0.0, 0.0) for v in out]


# 全局对齐后将模板 CA 映射到目标序列（P1/P3 核心）
def _align_template_to_target(
    target_seq: str,
    template_residues: list[str],
    template_coords: list[tuple[float, float, float]],
) -> tuple[list[str], list[tuple[float, float, float]], dict[str, float], list[tuple[int, int]]]:
    template_seq = "".join([r if r in AA3 else "G" for r in template_residues])
    aln_t, aln_q = _needleman_wunsch(target_seq, template_seq)
    mapped: list[tuple[float, float, float] | None] = [None] * len(target_seq)
    pairs: list[tuple[int, int]] = []

    i_t = 0
    i_q = 0
    matches = 0
    mapped_count = 0
    for ct, cq in zip(aln_t, aln_q):
        if ct != "-" and cq != "-":
            if i_t < len(target_seq) and i_q < len(template_coords):
                mapped[i_t] = template_coords[i_q]
                mapped_count += 1
                pairs.append((i_t, i_q))
                if ct == cq:
                    matches += 1
            i_t += 1
            i_q += 1
        elif ct != "-" and cq == "-":
            i_t += 1
        elif ct == "-" and cq != "-":
            i_q += 1
    aligned_coords = _interpolate_missing_coords(mapped)
    metrics = {
        "template_len": float(len(template_seq)),
        "target_len": float(len(target_seq)),
        "mapped_count": float(mapped_count),
        "identity_on_overlap": float(matches / mapped_count) if mapped_count else 0.0,
        "pair_count": float(len(pairs)),
    }
    return list(target_seq), aligned_coords, metrics, pairs


# ===========================================================================
# 配置加载与 CA 扰动/修复工具
# ===========================================================================
def _load_sources_config(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None:
        return {}
    if not path.exists():
        raise FileNotFoundError(f"Sources config not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Sources config must be a JSON object.")
    normalized: dict[str, dict[str, Any]] = {}
    for k, v in payload.items():
        if isinstance(v, dict):
            normalized[str(k)] = v
    return normalized


def _small_rotation_matrix(rng: random.Random, max_angle_rad: float = 0.06) -> np.ndarray:
    """小角度随机旋转（轴角表示）。"""
    axis = np.array([rng.gauss(0.0, 1.0), rng.gauss(0.0, 1.0), rng.gauss(0.0, 1.0)], dtype=float)
    n = float(np.linalg.norm(axis))
    if n < 1e-9:
        axis = np.array([1.0, 0.0, 0.0])
    else:
        axis = axis / n
    theta = rng.uniform(-max_angle_rad, max_angle_rad)
    x, y, z = axis
    k = np.array([[0.0, -z, y], [z, 0.0, -x], [-y, x, 0.0]])
    i3 = np.eye(3)
    return i3 + math.sin(theta) * k + (1.0 - math.cos(theta)) * (k @ k)


def _repair_ca_geometry(coords: list[tuple[float, float, float]]) -> list[tuple[float, float, float]]:
    """消除退化 CA 向量；相邻 CA 间距约 3.8 Å。"""
    if len(coords) <= 1:
        return coords
    out = [coords[0]]
    target = 3.8
    for i in range(1, len(coords)):
        prev = np.array(out[-1], dtype=float)
        nxt = np.array(coords[i], dtype=float)
        v = nxt - prev
        nv = float(np.linalg.norm(v))
        if nv < 1e-6:
            v = np.array([0.1, 0.0, target])
            nv = float(np.linalg.norm(v))
        v = v / nv * target
        out.append(tuple((prev + v).tolist()))
    return out


def _repair_short_ca_bonds(
    coords: list[tuple[float, float, float]],
    min_spacing: float = 2.5,
    target_spacing: float = 3.8,
) -> list[tuple[float, float, float]]:
    """仅修复过短的相邻 CA 键，保留大尺度运动。"""
    if len(coords) <= 1:
        return coords
    out = [np.array(coords[0], dtype=float)]
    arr = [np.array(c, dtype=float) for c in coords]
    for i in range(1, len(arr)):
        prev = out[-1]
        cur = arr[i].copy()
        v = cur - prev
        nv = float(np.linalg.norm(v))
        if nv < min_spacing:
            if nv < 1e-9 and i + 1 < len(arr):
                v = arr[i + 1] - prev
                nv = float(np.linalg.norm(v))
            if nv < 1e-9:
                v = np.array([0.0, 0.0, 1.0], dtype=float)
                nv = 1.0
            cur = prev + (v / nv) * target_spacing
        out.append(cur)
    return [tuple(float(x) for x in row) for row in out]


def _perturb_ca_coordinates(
    coords: list[tuple[float, float, float]],
    rng: random.Random,
    trans_mag: float = 0.2,
) -> list[tuple[float, float, float]]:
    arr = np.array(coords, dtype=float)
    c = arr.mean(axis=0)
    arr -= c
    r = _small_rotation_matrix(rng)
    arr = (r @ arr.T).T
    arr += c + np.array([rng.uniform(-trans_mag, trans_mag) for _ in range(3)])
    return [tuple(float(x) for x in row) for row in arr]


# ===========================================================================
# template_cif：mdtraj 全原子导出（可选刚体扰动，P2 设计）
# ===========================================================================
def _export_full_atom_cif(
    template_cif: Path,
    out_cif: Path,
    rng: random.Random,
    perturb: bool,
    target_len_hint: int | None = None,
) -> None:
    import mdtraj as md

    traj = _load_single_chain_protein_traj(template_cif, target_len_hint)
    frame = traj.slice(0, 1)
    if perturb:
        xyz = np.array(frame.xyz[0], dtype=float, copy=True)
        center = xyz.mean(axis=0)
        xyz -= center
        r = _small_rotation_matrix(rng)
        xyz = (r @ xyz.T).T
        xyz += center
        frame.xyz[0] = xyz
    out_cif.parent.mkdir(parents=True, exist_ok=True)
    frame.save_cif(str(out_cif))


def _resolve_template_list(
    root: Path,
    source_entry: dict[str, Any],
    primary: Path,
    n_conf: int,
) -> list[Path]:
    raw = source_entry.get("template_cifs")
    if isinstance(raw, list) and raw:
        paths = []
        for item in raw:
            p = Path(item)
            paths.append(p if p.is_absolute() else (root / p))
        out = []
        for i in range(n_conf):
            out.append(paths[i % len(paths)])
        return out
    return [primary] * n_conf


# ===========================================================================
# 仅 CA 的 mmCIF 写出（回退/中间结果）
# ===========================================================================
def _format_cif(problem_name: str, sequence: str, coords: list[tuple[float, float, float]]) -> str:
    lines: list[str] = []
    lines.append(f"data_{problem_name}")
    lines.append("#")
    lines.append("loop_")
    lines.append("_atom_site.group_PDB")
    lines.append("_atom_site.id")
    lines.append("_atom_site.type_symbol")
    lines.append("_atom_site.label_atom_id")
    lines.append("_atom_site.label_alt_id")
    lines.append("_atom_site.label_comp_id")
    lines.append("_atom_site.label_asym_id")
    lines.append("_atom_site.label_entity_id")
    lines.append("_atom_site.label_seq_id")
    lines.append("_atom_site.pdbx_PDB_ins_code")
    lines.append("_atom_site.Cartn_x")
    lines.append("_atom_site.Cartn_y")
    lines.append("_atom_site.Cartn_z")
    lines.append("_atom_site.occupancy")
    lines.append("_atom_site.B_iso_or_equiv")
    lines.append("_atom_site.pdbx_formal_charge")
    lines.append("_atom_site.auth_seq_id")
    lines.append("_atom_site.auth_comp_id")
    lines.append("_atom_site.auth_asym_id")
    lines.append("_atom_site.auth_atom_id")
    lines.append("_atom_site.pdbx_PDB_model_num")
    atom_id = 1
    for idx, (aa, (x, y, z)) in enumerate(zip(sequence, coords), start=1):
        comp = AA3.get(aa, "UNK")
        lines.append(
            f"ATOM {atom_id} C CA . {comp} A 1 {idx} ? "
            f"{x:.3f} {y:.3f} {z:.3f} 1.00 20.00 ? {idx} {comp} A CA 1"
        )
        atom_id += 1
    lines.append("#")
    return "\n".join(lines) + "\n"


# ===========================================================================
# RMSD 工具与 diversity_filter 筛选（P1）
# ===========================================================================
def _kabsch_rigid_rows(P: np.ndarray, Q: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """最小二乘刚体拟合 P->Q（行为三维点，单位埃）。

    返回 (R, t)，满足 x' = x @ R.T + t。
    """
    cP = P.mean(axis=0)
    cQ = Q.mean(axis=0)
    Pc = P - cP
    Qc = Q - cQ
    h = Pc.T @ Qc
    u, _, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0.0:
        vt[-1, :] *= -1.0
        r = vt.T @ u.T
    t = cQ - cP @ r.T
    return r, t


def _kabsch_ca_rmsd_angstrom(
    a: list[tuple[float, float, float]], b: list[tuple[float, float, float]]
) -> float:
    """等长 CA 坐标的 Kabsch RMSD（埃）。"""
    A = np.asarray(a, dtype=float)
    B = np.asarray(b, dtype=float)
    if A.shape != B.shape:
        raise ValueError("RMSD requires equal-shape coordinate arrays.")
    if A.shape[0] < 3:
        return float(np.sqrt(np.mean(np.sum((A - B) ** 2, axis=1))))
    cA = A.mean(axis=0)
    cB = B.mean(axis=0)
    Ac = A - cA
    Bc = B - cB
    h = Ac.T @ Bc
    u, _, vt = np.linalg.svd(h)
    r = vt.T @ u.T
    if np.linalg.det(r) < 0.0:
        vt[-1, :] *= -1.0
        r = vt.T @ u.T
    Bfit = Bc @ r.T
    return float(np.sqrt(np.mean(np.sum((Ac - Bfit) ** 2, axis=1))))


def _pairwise_ca_rmsd_matrix(coords_by_conf: list[list[tuple[float, float, float]]]) -> np.ndarray:
    """两两 Kabsch CA-RMSD 矩阵（埃）。"""
    n = len(coords_by_conf)
    mat = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(i + 1, n):
            d = _kabsch_ca_rmsd_angstrom(coords_by_conf[i], coords_by_conf[j])
            mat[i, j] = d
            mat[j, i] = d
    return mat


def _filter_outlier_indices_by_mean_distance(
    mat: np.ndarray,
    n_min_keep: int,
    trim_outlier_quantile: float,
    max_mean_distance: float,
) -> list[int]:
    """按平均两两距离剔除离群索引，必要时回退下界。"""
    n = int(mat.shape[0])
    if n <= n_min_keep:
        return list(range(n))
    means = mat.mean(axis=1)
    keep = list(range(n))
    if max_mean_distance < 1e9:
        keep = [i for i in keep if float(means[i]) <= max_mean_distance]
    q = float(trim_outlier_quantile)
    if 0.0 < q < 1.0 and keep:
        vals = np.array([float(means[i]) for i in keep], dtype=float)
        thr = float(np.quantile(vals, q))
        keep = [i for i in keep if float(means[i]) <= thr]
    if len(keep) < n_min_keep:
        order = sorted(range(n), key=lambda i: float(means[i]))
        keep = order[:n_min_keep]
    return keep


# P1 diversity_filter：基于 RMSD 的贪心子集选择
def _select_diverse_indices_by_rmsd(
    coords_by_conf: list[list[tuple[float, float, float]]],
    n_pick: int,
    min_pairwise_rmsd: float,
    max_pairwise_rmsd: float,
    pairwise_mat: np.ndarray | None = None,
) -> list[int]:
    """按两两 Kabsch RMSD 选取多样性均衡子集（埃）。"""
    n = len(coords_by_conf)
    if n_pick >= n or n <= 1:
        return list(range(min(n_pick, n)))

    mat = pairwise_mat if pairwise_mat is not None else _pairwise_ca_rmsd_matrix(coords_by_conf)

    # 从类 medoid 起点开始，结果更稳定
    mean_d = mat.mean(axis=1)
    selected = [int(np.argmin(mean_d))]
    remaining = [i for i in range(n) if i not in selected]
    target = (min_pairwise_rmsd + max_pairwise_rmsd) / 2.0

    while len(selected) < n_pick and remaining:
        best_i = remaining[0]
        best_bucket = 99
        best_score = float("inf")
        for i in remaining:
            ds = [float(mat[i, j]) for j in selected]
            dmin = min(ds)
            dmax = max(ds)
            if dmin >= min_pairwise_rmsd and dmax <= max_pairwise_rmsd:
                bucket = 0
            elif dmin >= min_pairwise_rmsd:
                bucket = 1
            else:
                bucket = 2
            # 分数越小越优
            # bucket0：dmin 接近目标区间中部
            # bucket1/2：偏好更紧簇，避免精度塌陷
            if bucket == 0:
                score = abs(dmin - target)
            else:
                score = dmin
            if bucket < best_bucket or (bucket == best_bucket and score < best_score):
                best_bucket = bucket
                best_score = score
                best_i = i
        selected.append(best_i)
        remaining = [i for i in remaining if i != best_i]
    return selected


# ===========================================================================
# hybrid 全原子：CA 骨架 + 模板侧链 + 避碰
# ===========================================================================
def _norm_row(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    if n < 1e-9:
        return np.array([1.0, 0.0, 0.0], dtype=float)
    return v / n


def _stub_ala_atoms_from_ca_env(
    ca_im1: np.ndarray, ca_i: np.ndarray, ca_ip1: np.ndarray
) -> list[tuple[str, str, float, float, float]]:
    """在 CA 周围构造近似 ALA 重原子（N, CA, C, O, CB，埃）。"""
    c = ca_i.astype(float)
    f = _norm_row(ca_ip1 - ca_i)
    b = _norm_row(ca_i - ca_im1)
    n_pos = c - 1.46 * _norm_row(b + f)
    c_pos = c + 1.52 * f
    side = np.cross(f, b)
    side = _norm_row(side)
    if float(np.linalg.norm(side)) < 1e-9:
        side = np.array([0.0, 1.0, 0.0], dtype=float)
    o_pos = c_pos + 1.23 * _norm_row(side + 0.25 * f)
    cb = c + 1.53 * side
    return [
        ("N", "N", float(n_pos[0]), float(n_pos[1]), float(n_pos[2])),
        ("CA", "C", float(c[0]), float(c[1]), float(c[2])),
        ("C", "C", float(c_pos[0]), float(c_pos[1]), float(c_pos[2])),
        ("O", "O", float(o_pos[0]), float(o_pos[1]), float(o_pos[2])),
        ("CB", "C", float(cb[0]), float(cb[1]), float(cb[2])),
    ]


def _element_symbol_for_atom(atom_name: str, md_element: Any) -> str:
    if md_element is not None and getattr(md_element, "symbol", None):
        s = str(md_element.symbol).strip().upper()
        if s:
            return s[0]
    n = atom_name.strip().upper()
    if n.startswith("CL"):
        return "C"
    if len(n) > 0 and n[0] in "CNOSHP":
        return n[0]
    return "C"


def _relieve_sidechain_clash(
    pos: np.ndarray,
    atom_name: str,
    residue_idx: int,
    placed_coords: list[np.ndarray],
    placed_residues: list[int],
    placed_buckets: dict[tuple[int, int, int], list[int]],
    enabled: bool,
    min_distance_a: float,
    max_iter: int = 6,
) -> np.ndarray:
    """将侧链原子移离已放置的非邻域重原子。"""
    if not enabled:
        return pos
    if atom_name.strip().upper() in {"N", "CA", "C", "O", "OXT"}:
        return pos
    out = np.array(pos, dtype=float, copy=True)
    cell = float(min_distance_a)
    for _ in range(max_iter):
        closest_j = -1
        closest_d = float("inf")
        key = tuple(np.floor(out / cell).astype(int).tolist())
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    neigh = (key[0] + dx, key[1] + dy, key[2] + dz)
                    for j in placed_buckets.get(neigh, []):
                        if abs(residue_idx - placed_residues[j]) <= 1:
                            continue
                        d = float(np.linalg.norm(out - placed_coords[j]))
                        if d < closest_d:
                            closest_d = d
                            closest_j = j
        if closest_j < 0 or closest_d >= min_distance_a:
            break
        direction = out - placed_coords[closest_j]
        n = float(np.linalg.norm(direction))
        if n < 1e-9:
            # 确定性回退方向，避免向提交结果引入额外随机性
            direction = np.array([1.0, 0.5, 0.25], dtype=float)
            n = float(np.linalg.norm(direction))
        out = placed_coords[closest_j] + (direction / n) * min_distance_a
    return out


def _relieve_atom_record_sidechains(
    records: list[dict[str, Any]],
    min_distance_a: float,
    max_passes: int = 3,
) -> None:
    """第二轮：相对记录列表中全部重原子做侧链避碰。"""
    cell = float(min_distance_a)
    for _ in range(max_passes):
        buckets: dict[tuple[int, int, int], list[int]] = {}
        for idx, rec in enumerate(records):
            key = tuple(np.floor(rec["pos"] / cell).astype(int).tolist())
            buckets.setdefault(key, []).append(idx)
        changed = False
        for i, rec in enumerate(records):
            if not rec["is_sidechain"]:
                continue
            pos = rec["pos"]
            closest_j = -1
            closest_d = float("inf")
            key = tuple(np.floor(pos / cell).astype(int).tolist())
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    for dz in (-1, 0, 1):
                        neigh = (key[0] + dx, key[1] + dy, key[2] + dz)
                        for j in buckets.get(neigh, []):
                            if i == j:
                                continue
                            other = records[j]
                            if abs(int(rec["residue_idx"]) - int(other["residue_idx"])) <= 1:
                                continue
                            d = float(np.linalg.norm(pos - other["pos"]))
                            if d < closest_d:
                                closest_d = d
                                closest_j = j
            if closest_j < 0 or closest_d >= min_distance_a:
                continue
            direction = pos - records[closest_j]["pos"]
            n = float(np.linalg.norm(direction))
            if n < 1e-9:
                direction = np.array([1.0, 0.5, 0.25], dtype=float)
                n = float(np.linalg.norm(direction))
            rec["pos"] = records[closest_j]["pos"] + (direction / n) * min_distance_a
            changed = True
        if not changed:
            break


def _write_hybrid_full_atom_cif(
    problem_name: str,
    target_seq: str,
    aligned_ca_coords: list[tuple[float, float, float]],
    pairs: list[tuple[int, int]],
    template_coords: list[tuple[float, float, float]],
    template_cif: Path,
    out_path: Path,
    relieve_sidechain_clashes: bool = False,
    sidechain_clash_min_a: float = 2.0,
    record_relief_passes: int = 3,
) -> None:
    """模板残基刚体对齐 CA；缺口处用近似 ALA 主链。"""
    import mdtraj as md

    _ = md
    if len(pairs) < 3:
        raise RuntimeError("hybrid export requires >=3 mapped CA pairs")
    tpl_for_target = dict(pairs)
    P = np.array([[template_coords[qi][k] for k in range(3)] for ti, qi in pairs], dtype=float)
    Q = np.array([[aligned_ca_coords[ti][k] for k in range(3)] for ti, qi in pairs], dtype=float)
    r, t = _kabsch_rigid_rows(P, Q)

    hint = len(target_seq)
    traj = _load_single_chain_protein_traj(template_cif, hint)
    ca_idx = traj.topology.select("name CA")
    ca_residues = [traj.topology.atom(int(i)).residue for i in ca_idx]
    if len(ca_residues) != len(template_coords):
        raise RuntimeError(
            f"Template CA/residue mismatch: n_ca_res={len(ca_residues)} n_tpl_coords={len(template_coords)}"
        )

    lines: list[str] = []
    lines.append(f"data_{problem_name}")
    lines.append("#")
    lines.append("loop_")
    lines.append("_atom_site.group_PDB")
    lines.append("_atom_site.id")
    lines.append("_atom_site.type_symbol")
    lines.append("_atom_site.label_atom_id")
    lines.append("_atom_site.label_alt_id")
    lines.append("_atom_site.label_comp_id")
    lines.append("_atom_site.label_asym_id")
    lines.append("_atom_site.label_entity_id")
    lines.append("_atom_site.label_seq_id")
    lines.append("_atom_site.pdbx_PDB_ins_code")
    lines.append("_atom_site.Cartn_x")
    lines.append("_atom_site.Cartn_y")
    lines.append("_atom_site.Cartn_z")
    lines.append("_atom_site.occupancy")
    lines.append("_atom_site.B_iso_or_equiv")
    lines.append("_atom_site.pdbx_formal_charge")
    lines.append("_atom_site.auth_seq_id")
    lines.append("_atom_site.auth_comp_id")
    lines.append("_atom_site.auth_asym_id")
    lines.append("_atom_site.auth_atom_id")
    lines.append("_atom_site.pdbx_PDB_model_num")

    atom_id = 1
    atom_records: list[dict[str, Any]] = []
    placed_coords: list[np.ndarray] = []
    placed_residues: list[int] = []
    placed_buckets: dict[tuple[int, int, int], list[int]] = {}
    bucket_cell = float(sidechain_clash_min_a)
    cas = np.array(aligned_ca_coords, dtype=float)
    lseq = len(target_seq)
    for ti in range(lseq):
        aa = target_seq[ti]
        comp = AA3.get(aa, "UNK")
        if ti in tpl_for_target:
            qi = tpl_for_target[ti]
            res = ca_residues[qi]
            for atom in res.atoms:
                nm = str(atom.name).strip()
                if atom.element and str(atom.element.symbol).strip().upper() == "H":
                    continue
                idx = int(atom.index)
                p_ang = traj.xyz[0, idx, :] * 10.0
                p_fit = p_ang @ r.T + t
                p_fit = _relieve_sidechain_clash(
                    p_fit,
                    nm,
                    ti,
                    placed_coords,
                    placed_residues,
                    placed_buckets,
                    enabled=relieve_sidechain_clashes,
                    min_distance_a=sidechain_clash_min_a,
                )
                sym = _element_symbol_for_atom(nm, atom.element)
                atom_records.append(
                    {
                        "id": atom_id,
                        "symbol": sym,
                        "name": nm[:4],
                        "comp": comp,
                        "residue_idx": ti,
                        "pos": np.array(p_fit, dtype=float),
                        "is_sidechain": nm.strip().upper() not in {"N", "CA", "C", "O", "OXT"},
                    }
                )
                placed_coords.append(np.array(p_fit, dtype=float))
                placed_residues.append(ti)
                key = tuple(np.floor(p_fit / bucket_cell).astype(int).tolist())
                placed_buckets.setdefault(key, []).append(len(placed_coords) - 1)
                atom_id += 1
        else:
            if lseq == 1:
                ca_prev = cas[0] - np.array([3.8, 0.0, 0.0], dtype=float)
                ca_next = cas[0] + np.array([3.8, 0.0, 0.0], dtype=float)
                stub = _stub_ala_atoms_from_ca_env(ca_prev, cas[0], ca_next)
            elif ti == 0:
                ca_next = cas[1]
                ca_prev = 2.0 * cas[0] - ca_next
                stub = _stub_ala_atoms_from_ca_env(ca_prev, cas[ti], ca_next)
            elif ti == lseq - 1:
                ca_prev = cas[ti - 1]
                ca_next = 2.0 * cas[ti] - ca_prev
                stub = _stub_ala_atoms_from_ca_env(ca_prev, cas[ti], ca_next)
            else:
                stub = _stub_ala_atoms_from_ca_env(cas[ti - 1], cas[ti], cas[ti + 1])
            for nm, sym, x, y, z in stub:
                p_stub = _relieve_sidechain_clash(
                    np.array([x, y, z], dtype=float),
                    nm,
                    ti,
                    placed_coords,
                    placed_residues,
                    placed_buckets,
                    enabled=relieve_sidechain_clashes,
                    min_distance_a=sidechain_clash_min_a,
                )
                atom_records.append(
                    {
                        "id": atom_id,
                        "symbol": sym,
                        "name": nm[:4],
                        "comp": comp,
                        "residue_idx": ti,
                        "pos": np.array(p_stub, dtype=float),
                        "is_sidechain": nm.strip().upper() not in {"N", "CA", "C", "O", "OXT"},
                    }
                )
                placed_coords.append(np.array(p_stub, dtype=float))
                placed_residues.append(ti)
                key = tuple(np.floor(p_stub / bucket_cell).astype(int).tolist())
                placed_buckets.setdefault(key, []).append(len(placed_coords) - 1)
                atom_id += 1
    if relieve_sidechain_clashes:
        _relieve_atom_record_sidechains(
            atom_records,
            min_distance_a=sidechain_clash_min_a,
            max_passes=max(1, int(record_relief_passes)),
        )
    for rec in atom_records:
        ti = int(rec["residue_idx"])
        p = rec["pos"]
        nm = str(rec["name"])
        comp = str(rec["comp"])
        lines.append(
            f"ATOM {int(rec['id'])} {rec['symbol']} {nm:<4} . {comp} A 1 {ti + 1} ? "
            f"{p[0]:.3f} {p[1]:.3f} {p[2]:.3f} 1.00 20.00 ? {ti + 1} {comp} A {nm} 1"
        )
    lines.append("#")
    out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


# ===========================================================================
# 生成后检查、agent.log、zip 打包
# ===========================================================================
def _self_check(out_dir: Path, problems: list[Problem]) -> None:
    try:
        import mdtraj as md
    except ImportError as exc:
        raise RuntimeError("mdtraj required for submission self-check.") from exc
    for p in problems:
        files = sorted(out_dir.glob(f"{p.problem_id}_conf*_pred.cif"))
        if not files:
            raise RuntimeError(f"No cif files generated for problem {p.problem_id}")
        if len(files) > 10:
            raise RuntimeError(f"Too many conformers for problem {p.problem_id}: {len(files)}")
        for f in files:
            txt = f.read_text(encoding="utf-8")
            if "_atom_site" not in txt or "ATOM " not in txt:
                raise RuntimeError(f"Invalid CIF content: {f}")
            if " NaN" in txt or " inf" in txt.lower():
                raise RuntimeError(f"Non-physical coordinates found: {f}")
            t = md.load(str(f))
            if not np.isfinite(t.xyz).all():
                raise RuntimeError(f"Non-finite coordinates in {f}")
            if t.n_atoms == 0:
                raise RuntimeError(f"Empty structure: {f}")


def _build_agent_log(
    out_dir: Path,
    problems: list[Problem],
    note: str,
    strategy_report: dict[str, Any],
) -> None:
    lines = []
    lines.append("Agent Log: Protein Conformational Ensemble Generation")
    lines.append("Stage 1 - Literature/Task parsing: loaded problem JSON and constraints.")
    lines.append("Stage 2 - Bottleneck diagnosis: evaluated available trajectory and sequence constraints.")
    lines.append("Stage 3 - Code evolution: generated mmCIF conformers by selected strategy per problem.")
    lines.append("Stage 4 - Experiment and iteration: performed format checks and zip packaging.")
    lines.append("")
    lines.append("Problem summary:")
    for p in problems:
        lines.append(
            f"- problem_id={p.problem_id}, name={p.name}, seq_len={len(p.sequence)}, "
            f"requested_conformers={p.conformer_count}"
        )
    lines.append("")
    lines.append("Strategy report:")
    for key, info in strategy_report.items():
        lines.append(f"- problem_id={key}: {json.dumps(info, ensure_ascii=False)}")
    lines.append("")
    lines.append(_AGENT_LOG_STAGE5_HEADING)
    lines.append(
        "  - Literature trace: map design choices to diffusion/flow/MD+MSM literature "
        "and record citations or URLs consulted."
    )
    lines.append(
        "  - Methods narrative: data sources (public PDB/AFDB only), software versions, "
        "random seeds, and reproducible command lines."
    )
    lines.append(
        "  - Results linkage: each figure/table tied to one claim; avoid orphan metrics "
        "(see readme Prompt 08 / 11 / 12)."
    )
    lines.append(
        "  - Discussion & limits: sampling length, force-field bias, template coverage, "
        "and what would falsify the model."
    )
    lines.append(
        "  - Reviewer rehearsal: pre-empt 3–5 hard questions with evidence-based replies "
        "(inspired by multi-agent critique loops in open-source paper agents)."
    )
    lines.append("")
    lines.append(_AGENT_LOG_STAGE6_HEADING)
    lines.append(
        "  - document/rull.md does not require an HTTP API for the contestant repo; "
        "this line records a voluntary convention if you later expose REST."
    )
    lines.append(
        "  - On client error use 4xx, on server failure use 5xx; never return HTTP 200 "
        "with a logical failure payload."
    )
    lines.append(
        '  - Error JSON shape: {"error":{"code":"<string>","message":"<string>",'
        '"requestId":"<string>"}} (requestId empty or omitted for offline CLI).'
    )
    if note:
        lines.append("")
        lines.append(f"Note: {note}")
    (out_dir / "agent.log").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _zip_output(out_dir: Path, zip_path: Path) -> None:
    """仅将赛题文件名（*_pred.cif、agent.log）打入 output.zip。"""
    members = sorted(
        p
        for p in out_dir.iterdir()
        if p.is_file() and _SUBMISSION_CIF_RE.match(p.name)
    )
    log_file = out_dir / "agent.log"
    if not log_file.exists():
        raise FileNotFoundError("agent.log not found in output directory.")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for member in members:
            zf.write(member, arcname=member.name)
        zf.write(log_file, arcname="agent.log")


# ===========================================================================
# 命令行参数
# ===========================================================================
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成赛题格式的 output.zip")
    parser.add_argument(
        "--problems-dir",
        default="document",
        help="含 1.json、2.json、3.json 的目录",
    )
    parser.add_argument(
        "--out-dir",
        default="results/submission",
        help="写出 cif 与 agent.log 的目录",
    )
    parser.add_argument(
        "--zip-name",
        default="output.zip",
        help="输出 zip 文件名",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="随机种子（构象扰动可复现）",
    )
    parser.add_argument(
        "--note",
        default="",
        help="可选：写入 agent.log 的备注",
    )
    parser.add_argument(
        "--strategy",
        choices=["baseline_ca", "auto", "template_cif", "template_align", "trajectory_ca"],
        default="auto",
        help="构象生成策略（默认 auto）",
    )
    parser.add_argument(
        "--traj-path",
        default="results/openmm/traj.dcd",
        help="auto 策略使用的轨迹路径",
    )
    parser.add_argument(
        "--top-path",
        default="results/openmm/final.pdb",
        help="auto 策略使用的拓扑路径",
    )
    parser.add_argument(
        "--sources-config",
        default="",
        help="可选：每题数据源/策略的 JSON 配置",
    )
    parser.add_argument(
        "--with-local-eval",
        action="store_true",
        help="打包后运行 eval_submission_local.py",
    )
    parser.add_argument(
        "--eval-gt-dir",
        default="",
        help="可选：本地评测用的 GT mmCIF 目录",
    )
    parser.add_argument(
        "--eval-out-json",
        default="",
        help="本地评测报告路径（默认 <out-dir>/local_eval.json）",
    )
    parser.add_argument(
        "--agent-log-from",
        default="",
        help="复制已有 agent.log，而非重新生成（审核复现）",
    )
    return parser.parse_args()


# ===========================================================================
# 主流程：按题策略分发 -> mmCIF -> zip
# ===========================================================================
def main() -> None:
    args = parse_args()
    # Project 根目录：配置与 CLI 相对路径均相对此处解析
    root = Path(__file__).resolve().parents[1]
    problems_dir = Path(args.problems_dir)
    problems_dir = problems_dir if problems_dir.is_absolute() else (root / problems_dir)
    out_dir = Path(args.out_dir)
    out_dir = out_dir if out_dir.is_absolute() else (root / out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    sources_cfg_path = Path(args.sources_config) if args.sources_config else None
    if sources_cfg_path and not sources_cfg_path.is_absolute():
        sources_cfg_path = root / sources_cfg_path

    problems = []
    for problem_id in (1, 2, 3):
        path = problems_dir / f"{problem_id}.json"
        if not path.exists():
            raise FileNotFoundError(f"Missing problem file: {path}")
        problems.append(_load_problem(path, problem_id))

    strategy_report: dict[str, Any] = {}
    sources_cfg = _load_sources_config(sources_cfg_path)
    # 默认轨迹/拓扑占位（审核包配置中通常未使用）
    traj_path = Path(args.traj_path)
    traj_path = traj_path if traj_path.is_absolute() else (root / traj_path)
    top_path = Path(args.top_path)
    top_path = top_path if top_path.is_absolute() else (root / top_path)

    for p in problems:
        # --- 按题循环：每题最多 10 个构象（赛规上限）---
        n_conf = min(p.conformer_count, 10)
        used_strategy = "baseline_ca"
        reason = "default"
        coords_by_conf: list[list[tuple[float, float, float]]] = []
        seq_for_output = p.sequence
        hybrid_meta: list[dict[str, Any] | None] = [None] * n_conf

        source_entry = sources_cfg.get(str(p.problem_id), {})

        # --- 按 JSON 策略生成构象（模板 / 轨迹 / 基线）---
        export_mode = str(source_entry.get("export_mode", "auto")).lower()
        full_atom = bool(source_entry.get("full_atom", True))
        repair_hybrid_short_ca = bool(source_entry.get("repair_hybrid_short_ca", False))
        hybrid_short_ca_min = float(source_entry.get("hybrid_short_ca_min_A", 2.5))
        relieve_hybrid_sidechain_clashes = bool(
            source_entry.get("relieve_hybrid_sidechain_clashes", False)
        )
        hybrid_sidechain_clash_min = float(source_entry.get("hybrid_sidechain_clash_min_A", 2.0))
        hybrid_sidechain_record_passes = int(source_entry.get("hybrid_sidechain_record_passes", 3))
        local_strategy = str(source_entry.get("strategy", args.strategy))
        local_traj = Path(source_entry.get("traj_path", str(traj_path)))
        local_top = Path(source_entry.get("top_path", str(top_path)))
        local_template = Path(source_entry.get("template_cif", ""))
        local_traj = local_traj if local_traj.is_absolute() else (root / local_traj)
        local_top = local_top if local_top.is_absolute() else (root / local_top)
        local_template = local_template if local_template.is_absolute() else (root / local_template)

        # 分支 1：OpenMM 轨迹 CA 聚类（路径存在且长度匹配时）
        if local_strategy in ("auto", "trajectory_ca") and local_traj.exists() and local_top.exists():
            try:
                traj_residues, traj_coords = _extract_ca_from_trajectory(
                    traj_path=local_traj,
                    top_path=local_top,
                    n_conformers=n_conf,
                )
                if len(traj_residues) == len(p.sequence):
                    used_strategy = "trajectory_ca"
                    reason = "trajectory length matches target sequence length"
                    coords_by_conf = traj_coords
                    seq_for_output = "".join([r if r in AA3 else "G" for r in traj_residues])
                else:
                    reason = (
                        f"trajectory length mismatch (traj={len(traj_residues)}, "
                        f"target={len(p.sequence)}), fallback baseline"
                    )
            except Exception as exc:
                reason = f"trajectory strategy failed ({exc}), fallback baseline"
        elif local_strategy == "trajectory_ca":
            reason = "trajectory_ca requested but traj/top path missing, fallback baseline"
        # 分支 2：template_cif / template_align / auto 且模板路径有效
        elif local_strategy in ("template_cif", "template_align", "auto") and str(local_template) and local_template.exists():
            try:
                if local_strategy == "template_align":
                    diversity_cfg = source_entry.get("diversity_filter", {})
                    use_diversity_filter = bool(
                        isinstance(diversity_cfg, dict) and diversity_cfg.get("enabled", False)
                    )
                    candidate_multiplier = 1
                    min_pw_rmsd = 0.0
                    max_pw_rmsd = 1e9
                    trim_quantile = 1.0
                    max_mean_distance = 1e9
                    if use_diversity_filter:
                        candidate_multiplier = max(
                            1, int(diversity_cfg.get("candidate_multiplier", 2))
                        )
                        min_pw_rmsd = float(diversity_cfg.get("min_pairwise_rmsd_A", 1.0))
                        max_pw_rmsd = float(diversity_cfg.get("max_pairwise_rmsd_A", 8.0))
                        trim_quantile = float(diversity_cfg.get("trim_outlier_quantile", 1.0))
                        max_mean_distance = float(diversity_cfg.get("max_mean_distance_A", 1e9))
                    n_candidates = min(10, max(n_conf, n_conf * candidate_multiplier))
                    tpl_paths = _resolve_template_list(root, source_entry, local_template, n_candidates)
                    max_slip = int(source_entry.get("full_atom_max_slip", 32))
                    want_hybrid = bool(source_entry.get("align_hybrid_full_atom", True))
                    buf_coords: list[list[tuple[float, float, float]]] = []
                    buf_hybrid: list[dict[str, Any] | None] = []
                    reason_parts: list[str] = []
                    seq_aligned_ref: list[str] | None = None
                    for conf_i in range(n_candidates):
                        tp = tpl_paths[conf_i]
                        tpl_res, tpl_coords = _extract_ca_from_cif(tp, len(p.sequence))
                        seq_aligned, coords_aligned, metrics, pairs = _align_template_to_target(
                            target_seq=p.sequence,
                            template_residues=tpl_res,
                            template_coords=tpl_coords,
                        )
                        if seq_aligned_ref is None:
                            seq_aligned_ref = seq_aligned
                        buf_coords.append(coords_aligned[:])
                        hybrid_ok = (
                            full_atom
                            and export_mode != "ca_only"
                            and want_hybrid
                            and abs(len(tpl_res) - len(p.sequence)) <= max_slip
                            and len(pairs) >= 3
                        )
                        if hybrid_ok:
                            buf_hybrid.append(
                                {
                                    "template": tp,
                                    "pairs": pairs,
                                    "tpl_coords": tpl_coords,
                                    "metrics": metrics,
                                }
                            )
                        else:
                            buf_hybrid.append(None)
                        reason_parts.append(
                            f"{tp.name}: id={metrics['identity_on_overlap']:.3f}, "
                            f"map={int(metrics['mapped_count'])}/{len(p.sequence)}, "
                            f"hybrid={'y' if hybrid_ok else 'n'}"
                        )
                    coords_by_conf = buf_coords
                    hybrid_meta = buf_hybrid
                    if use_diversity_filter and len(coords_by_conf) > n_conf:
                        pw = _pairwise_ca_rmsd_matrix(coords_by_conf)
                        pre_keep = _filter_outlier_indices_by_mean_distance(
                            pw, n_conf, trim_quantile, max_mean_distance
                        )
                        if len(pre_keep) < len(coords_by_conf):
                            sub_coords = [coords_by_conf[i] for i in pre_keep]
                            sub_hybrid = [hybrid_meta[i] for i in pre_keep]
                            sub_pw = pw[np.ix_(pre_keep, pre_keep)]
                        else:
                            sub_coords = coords_by_conf
                            sub_hybrid = hybrid_meta
                            sub_pw = pw
                        keep_local = _select_diverse_indices_by_rmsd(
                            sub_coords,
                            n_conf,
                            min_pw_rmsd,
                            max_pw_rmsd,
                            pairwise_mat=sub_pw,
                        )
                        keep = [pre_keep[i] for i in keep_local] if len(pre_keep) < len(coords_by_conf) else keep_local
                        coords_by_conf = [coords_by_conf[i] for i in keep]
                        hybrid_meta = [hybrid_meta[i] for i in keep]
                        reason_parts.append(
                            f"diversity_filter keep={keep} from {n_candidates} "
                            f"(min={min_pw_rmsd:.2f}A,max={max_pw_rmsd:.2f}A,"
                            f"trim_q={trim_quantile:.2f},max_mean={max_mean_distance:.2f}A)"
                        )
                    used_strategy = "template_align"
                    seq_for_output = "".join([r if r in AA3 else "G" for r in (seq_aligned_ref or [])])
                    reason = "aligned templates: " + "; ".join(reason_parts)
                else:
                    tpl_res, tpl_coords = _extract_ca_from_cif(local_template, len(p.sequence))
                    if len(tpl_res) == len(p.sequence):
                        used_strategy = "template_cif"
                        reason = f"template_cif length matches target ({local_template.name})"
                        seq_for_output = "".join([r if r in AA3 else "G" for r in tpl_res])
                        coords_by_conf = [tpl_coords[:] for _ in range(n_conf)]
                    else:
                        reason = (
                            f"template length mismatch (tpl={len(tpl_res)}, target={len(p.sequence)}), "
                            "fallback baseline"
                        )
            except Exception as exc:
                reason = f"template_cif strategy failed ({exc}), fallback baseline"
        elif local_strategy == "template_cif":
            reason = "template_cif requested but template path missing, fallback baseline"
        elif local_strategy == "template_align":
            reason = "template_align requested but template path missing, fallback baseline"

        # 分支 3：模板/轨迹未产出坐标时回退 baseline_ca
        if not coords_by_conf:
            coords_by_conf = [
                _build_ca_coordinates(p.sequence, conf_idx=conf_idx, seed=args.seed + p.problem_id)
                for conf_idx in range(1, n_conf + 1)
            ]

        tpl_len_ok = False
        if str(local_template) and local_template.exists():
            try:
                tr_check, _ = _extract_ca_from_cif(local_template, len(p.sequence))
                tpl_len_ok = len(tr_check) == len(p.sequence)
            except Exception:
                tpl_len_ok = False

        use_mdtraj_full = (
            tpl_len_ok
            and full_atom
            and export_mode != "ca_only"
            and used_strategy == "template_cif"
        )

        tpl_paths_resolved = _resolve_template_list(root, source_entry, local_template, n_conf)

        if not use_mdtraj_full:
            repaired: list[list[tuple[float, float, float]]] = []
            for i, coords in enumerate(coords_by_conf):
                if hybrid_meta[i] is not None:
                    if repair_hybrid_short_ca:
                        repaired.append(_repair_short_ca_bonds(coords, min_spacing=hybrid_short_ca_min))
                    else:
                        repaired.append(coords)
                else:
                    rc = _repair_ca_geometry(coords)
                    rng = random.Random(args.seed + p.problem_id * 1000 + (i + 1))
                    repaired.append(_perturb_ca_coordinates(rc, rng, trans_mag=0.15))
            coords_by_conf = repaired

        # 每个构象写一个 mmCIF：全原子 / hybrid / 仅 CA
        for conf_idx in range(1, n_conf + 1):
            filename = f"{p.problem_id}_conf{conf_idx}_pred.cif"
            out_path = out_dir / filename
            if use_mdtraj_full:
                rng = random.Random(args.seed + p.problem_id * 1000 + conf_idx)
                _export_full_atom_cif(
                    tpl_paths_resolved[conf_idx - 1],
                    out_path,
                    rng,
                    perturb=True,
                    target_len_hint=len(seq_for_output),
                )
            elif hybrid_meta[conf_idx - 1] is not None:
                h = hybrid_meta[conf_idx - 1]
                assert h is not None
                _write_hybrid_full_atom_cif(
                    p.name,
                    seq_for_output,
                    coords_by_conf[conf_idx - 1],
                    h["pairs"],
                    h["tpl_coords"],
                    Path(h["template"]),
                    out_path,
                    relieve_sidechain_clashes=relieve_hybrid_sidechain_clashes,
                    sidechain_clash_min_a=hybrid_sidechain_clash_min,
                    record_relief_passes=hybrid_sidechain_record_passes,
                )
            else:
                coords = coords_by_conf[conf_idx - 1]
                out_path.write_text(_format_cif(p.name, seq_for_output, coords), encoding="utf-8")
        strategy_report[str(p.problem_id)] = {
            "strategy": used_strategy,
            "reason": reason,
            "conformers": n_conf,
            "sequence_length": len(seq_for_output),
            "requested_strategy": local_strategy,
            "traj_path": str(local_traj),
            "top_path": str(local_top),
            "template_cif": str(local_template),
            "export": {
                "mdtraj_full_atom": use_mdtraj_full,
                "full_atom_config": full_atom,
                "export_mode": export_mode,
                "hybrid_full_atom_conformers": sum(1 for h in hybrid_meta if h is not None),
                "repair_hybrid_short_ca": repair_hybrid_short_ca,
                "hybrid_short_ca_min_A": hybrid_short_ca_min,
                "relieve_hybrid_sidechain_clashes": relieve_hybrid_sidechain_clashes,
                "hybrid_sidechain_clash_min_A": hybrid_sidechain_clash_min,
                "hybrid_sidechain_record_passes": hybrid_sidechain_record_passes,
            },
        }

    # 校验 mmCIF、写入 agent.log、打包 zip（可选本地评测）
    _self_check(out_dir, problems)
    # 审核：复制冻结的 agent.log（相对 Project 根目录）
    if args.agent_log_from.strip():
        agent_src = Path(args.agent_log_from.strip())
        agent_src = agent_src if agent_src.is_absolute() else (root / agent_src)
        if not agent_src.is_file():
            raise FileNotFoundError(f"--agent-log-from not found: {agent_src}")
        shutil.copy2(agent_src, out_dir / "agent.log")
    else:
        _build_agent_log(out_dir, problems, note=args.note.strip(), strategy_report=strategy_report)
    (out_dir / "strategy_report.json").write_text(
        json.dumps(strategy_report, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    zip_path = out_dir / args.zip_name
    _zip_output(out_dir, zip_path)
    if zip_path.stat().st_size > 100 * 1024 * 1024:
        raise RuntimeError(f"{zip_path} exceeds 100MB limit.")

    if args.with_local_eval:
        eval_script = Path(__file__).resolve().parent / "eval_submission_local.py"
        if not eval_script.is_file():
            raise FileNotFoundError(f"Missing local eval script: {eval_script}")
        eval_out = (
            Path(args.eval_out_json)
            if args.eval_out_json.strip()
            else (out_dir / "local_eval.json")
        )
        eval_out = eval_out if eval_out.is_absolute() else (root / eval_out)
        eval_cmd = [
            sys.executable,
            str(eval_script),
            "--zip",
            str(zip_path),
            "--problems-dir",
            str(problems_dir),
            "--out-json",
            str(eval_out),
        ]
        if args.eval_gt_dir.strip():
            gt = Path(args.eval_gt_dir.strip())
            gt = gt if gt.is_absolute() else (root / gt)
            eval_cmd += ["--gt-dir", str(gt)]
        print(f"[STEP] Local eval: {' '.join(eval_cmd)}", flush=True)
        result = subprocess.run(eval_cmd, cwd=str(root), check=False)
        if result.returncode != 0:
            raise RuntimeError(f"Local eval failed (exit code {result.returncode})")
        print(f"[DONE] Local eval JSON: {eval_out}")

    print(f"[DONE] Submission directory: {out_dir}")
    print(f"[DONE] Zip package: {zip_path}")
    print(f"[DONE] Zip size: {zip_path.stat().st_size / (1024*1024):.2f} MB")


if __name__ == "__main__":
    main()
