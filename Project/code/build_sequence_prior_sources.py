#!/usr/bin/env python
"""离线训练辅助：将 ColabFold 序列先验合并进 submission_sources JSON。

由 python code/main.py build-prior 调用。
扫描 --candidate-root（默认 processed_data/colabfold），写出相对 Project 根的路径。
不运行 ColabFold，仅读取已有 PDB/mmCIF。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

CandidateSortMode = Literal["path", "mtime_desc"]

# 在 problem_{1,2,3}/ 下扫描的结构文件后缀
STRUCTURE_SUFFIXES = {".cif", ".mmcif", ".pdb"}


# ---------------------------------------------------------------------------
# 路径工具
# ---------------------------------------------------------------------------
def _project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _as_repo_relative(root: Path, path: Path) -> str:
    """返回相对 Project 根目录的 posix 路径，用于 JSON 配置。"""
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _read_problem_length(root: Path, problem_id: int) -> int:
    """从 data/{id}.json（Docker）或 document/{id}.json（本地）读取序列长度。"""
    for problem_json in (
        root / "data" / f"{problem_id}.json",
        root / "document" / f"{problem_id}.json",
    ):
        if not problem_json.is_file():
            continue
        payload = json.loads(problem_json.read_text(encoding="utf-8"))
        seq = payload[0]["sequences"][0]["proteinChain"]["sequence"].strip()
        return len(seq)
    raise FileNotFoundError(f"problem JSON missing for id={problem_id} under {root}")


# ---------------------------------------------------------------------------
# 候选结构校验（CA 数量、平均 pLDDT）
# ---------------------------------------------------------------------------
def _ca_count(path: Path) -> int:
    import mdtraj as md

    traj = md.load(str(path))
    return int(len(traj.topology.select("name CA")))


def _colabfold_scores_json_for_structure(path: Path) -> Path | None:
    """ColabFold 在 ``{stem}_unrelaxed_...pdb`` 旁写出 ``{stem}_scores_...json``。"""
    stem = path.stem
    if "_unrelaxed_" not in stem:
        return None
    scores_stem = stem.replace("_unrelaxed_", "_scores_", 1)
    candidate = path.parent / f"{scores_stem}.json"
    return candidate if candidate.is_file() else None


def _mean_plddt(path: Path) -> float | None:
    """从 ColabFold scores JSON 或 PDB B 因子读取平均 pLDDT。"""
    scores = _colabfold_scores_json_for_structure(path)
    if scores is not None:
        payload = json.loads(scores.read_text(encoding="utf-8"))
        raw = payload.get("plddt")
        if isinstance(raw, list) and raw:
            return float(sum(float(x) for x in raw) / len(raw))
    if path.suffix.lower() != ".pdb":
        return None
    try:
        import mdtraj as md
    except ImportError:
        return None
    traj = md.load(str(path))
    ca = traj.topology.select("name CA")
    if len(ca) == 0:
        return None
    bf = traj.bfactors[ca]
    if bf.ndim > 1:
        bf = bf[:, 0]
    return float(bf.mean())


def _sorted_structure_paths(paths: list[Path], sort_mode: CandidateSortMode) -> list[Path]:
    if sort_mode == "mtime_desc":

        def sort_key(p: Path) -> tuple[float, str]:
            try:
                return (-float(p.stat().st_mtime), str(p))
            except OSError:
                return (0.0, str(p))

        return sorted(paths, key=sort_key)
    return sorted(paths, key=lambda p: str(p))


def _scan_problem_structures(
    root: Path,
    search_root: Path,
    problem_id: int,
    validate_candidates: bool,
    max_length_delta: int,
    candidate_sort: CandidateSortMode,
    min_mean_plddt: float,
) -> tuple[list[str], list[dict[str, Any]]]:
    """列出某题在 search_root 下通过/拒绝的结构路径。"""
    problem_dir = search_root / f"problem_{problem_id}"
    if not problem_dir.exists():
        return [], []
    target_len = _read_problem_length(root, problem_id)
    raw_paths = [
        p
        for p in problem_dir.rglob("*")
        if p.is_file() and p.suffix.lower() in STRUCTURE_SUFFIXES
    ]
    found = []
    rejected = []
    for path in _sorted_structure_paths(raw_paths, candidate_sort):
        rel = _as_repo_relative(root, path)
        if not validate_candidates:
            found.append(rel)
            continue
        try:
            n_ca = _ca_count(path)
        except Exception as exc:
            rejected.append({"path": rel, "reason": f"load_failed: {exc}"})
            continue
        delta = abs(n_ca - target_len)
        if delta > max_length_delta:
            rejected.append(
                {
                    "path": rel,
                    "reason": f"ca_length_mismatch: ca={n_ca}, target={target_len}, delta={delta}",
                }
            )
            continue
        if min_mean_plddt > 0:
            mean_plddt = _mean_plddt(path)
            if mean_plddt is None:
                rejected.append({"path": rel, "reason": "plddt_unavailable"})
                continue
            if mean_plddt < min_mean_plddt:
                rejected.append(
                    {
                        "path": rel,
                        "reason": f"plddt_below_threshold: mean={mean_plddt:.2f}, min={min_mean_plddt:.2f}",
                    }
                )
                continue
        found.append(rel)
    return found, rejected


def _dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


# ---------------------------------------------------------------------------
# 将扫描到的先验合并进基础 submission_sources JSON
# ---------------------------------------------------------------------------
def build_sources(
    root: Path,
    base_config: Path,
    candidate_roots: list[Path],
    prefer_sequence_prior: bool,
    validate_candidates: bool,
    max_length_delta: int,
    candidate_sort: CandidateSortMode = "path",
    max_prior_per_problem: int = 0,
    min_mean_plddt: float = 50.0,
) -> dict[str, Any]:
    payload = json.loads(base_config.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Base config must be a JSON object: {base_config}")

    for pid in (1, 2, 3):
        key = str(pid)
        entry = payload.get(key)
        if not isinstance(entry, dict):
            continue
        prior_paths = []
        rejected = []
        for candidate_root in candidate_roots:
            found_one, rejected_one = _scan_problem_structures(
                root=root,
                search_root=candidate_root,
                problem_id=pid,
                validate_candidates=validate_candidates,
                max_length_delta=max_length_delta,
                candidate_sort=candidate_sort,
                min_mean_plddt=min_mean_plddt,
            )
            prior_paths.extend(found_one)
            rejected.extend(rejected_one)
        prior_paths = _dedupe_keep_order(prior_paths)
        cap = max(0, int(max_prior_per_problem))
        if cap > 0 and len(prior_paths) > cap:
            entry["sequence_prior_cap"] = {"before": len(prior_paths), "after": cap}
            prior_paths = prior_paths[:cap]
        else:
            entry.pop("sequence_prior_cap", None)
        entry["sequence_prior_rejected"] = rejected
        if not prior_paths:
            entry["sequence_prior_candidates"] = []
            continue

        existing = entry.get("template_cifs", [])
        if not isinstance(existing, list):
            existing = []
        existing_str = [str(x) for x in existing]
        merged = prior_paths + existing_str if prefer_sequence_prior else existing_str + prior_paths
        entry["template_cifs"] = _dedupe_keep_order(merged)
        entry["sequence_prior_candidates"] = prior_paths
        if prefer_sequence_prior:
            entry["template_cif"] = prior_paths[0]
        payload[key] = entry
    return payload


def _build_summary(
    payload: dict[str, Any],
    base_config: Path,
    candidate_roots: list[Path],
    out_config: Path,
    prefer_sequence_prior: bool,
    validate_candidates: bool,
    max_length_delta: int,
    candidate_sort: CandidateSortMode,
    max_prior_per_problem: int,
    min_mean_plddt: float,
) -> dict[str, Any]:
    """写出合并配置旁的审计 summary JSON。"""
    problems: dict[str, Any] = {}
    for pid in ("1", "2", "3"):
        entry = payload.get(pid, {})
        if not isinstance(entry, dict):
            continue
        candidates = entry.get("sequence_prior_candidates", [])
        rejected = entry.get("sequence_prior_rejected", [])
        cap_meta = entry.get("sequence_prior_cap") if isinstance(entry, dict) else None
        problems[pid] = {
            "accepted_count": len(candidates) if isinstance(candidates, list) else 0,
            "rejected_count": len(rejected) if isinstance(rejected, list) else 0,
            "accepted": candidates if isinstance(candidates, list) else [],
            "rejected": rejected if isinstance(rejected, list) else [],
            "prior_cap": cap_meta if isinstance(cap_meta, dict) else None,
        }
    return {
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "base_config": str(base_config),
        "candidate_roots": [str(p) for p in candidate_roots],
        "out_config": str(out_config),
        "prefer_sequence_prior": prefer_sequence_prior,
        "validate_candidates": validate_candidates,
        "max_length_delta": max_length_delta,
        "candidate_sort": candidate_sort,
        "max_prior_per_problem": max_prior_per_problem,
        "min_mean_plddt": min_mean_plddt,
        "problems": problems,
    }


# ---------------------------------------------------------------------------
# 命令行
# ---------------------------------------------------------------------------
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将本地序列先验预测合并进 submission 源配置"
    )
    parser.add_argument(
        "--base-config",
        default="configs/submission_sources.public.json",
        help="待扩展的基础 sources 配置",
    )
    parser.add_argument(
        "--candidate-root",
        default="results/colabfold",
        help="主扫描根目录（含 problem_1/2/3 预测子目录）",
    )
    parser.add_argument(
        "--extra-candidate-root",
        action="append",
        default=[],
        help="额外扫描根目录（可多次指定）",
    )
    parser.add_argument(
        "--out-config",
        default="configs/submission_sources.sequence_prior.json",
        help="输出的 sources 配置路径",
    )
    parser.add_argument(
        "--report-json",
        default="results/sequence_prior/summary.json",
        help="候选审计 summary JSON 路径",
    )
    parser.add_argument(
        "--prefer-sequence-prior",
        action="store_true",
        help="序列先验排在公开模板之前，并将 template_cif 设为首个命中",
    )
    parser.add_argument(
        "--no-validate-candidates",
        action="store_true",
        help="合并前不做 mdtraj CA 长度校验",
    )
    parser.add_argument(
        "--max-length-delta",
        type=int,
        default=0,
        help="校验时允许的 |CA 数 - 赛题序列长度| 上限",
    )
    parser.add_argument(
        "--candidate-sort",
        choices=("path", "mtime_desc"),
        default="path",
        help="每题文件排序：path 字典序（默认）或 mtime_desc 最新优先",
    )
    parser.add_argument(
        "--max-prior-per-problem",
        type=int,
        default=0,
        help="去重后每题最多保留的先验路径数（0 表示不限制）",
    )
    parser.add_argument(
        "--min-mean-plddt",
        type=float,
        default=50.0,
        help="平均 pLDDT 低于此值则拒绝（0 表示关闭）",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = _project_root()
    base_config = Path(args.base_config)
    base_config = base_config if base_config.is_absolute() else (root / base_config)
    candidate_root = Path(args.candidate_root)
    candidate_root = candidate_root if candidate_root.is_absolute() else (root / candidate_root)
    candidate_roots = [candidate_root]
    for item in args.extra_candidate_root:
        p = Path(item)
        candidate_roots.append(p if p.is_absolute() else (root / p))
    out_config = Path(args.out_config)
    out_config = out_config if out_config.is_absolute() else (root / out_config)
    report_json = Path(args.report_json)
    report_json = report_json if report_json.is_absolute() else (root / report_json)

    payload = build_sources(
        root=root,
        base_config=base_config,
        candidate_roots=candidate_roots,
        prefer_sequence_prior=bool(args.prefer_sequence_prior),
        validate_candidates=not bool(args.no_validate_candidates),
        max_length_delta=int(args.max_length_delta),
        candidate_sort=args.candidate_sort,  # type: ignore[arg-type]
        max_prior_per_problem=int(args.max_prior_per_problem),
        min_mean_plddt=float(args.min_mean_plddt),
    )
    out_config.parent.mkdir(parents=True, exist_ok=True)
    out_config.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = _build_summary(
        payload=payload,
        base_config=base_config,
        candidate_roots=candidate_roots,
        out_config=out_config,
        prefer_sequence_prior=bool(args.prefer_sequence_prior),
        validate_candidates=not bool(args.no_validate_candidates),
        max_length_delta=int(args.max_length_delta),
        candidate_sort=args.candidate_sort,  # type: ignore[arg-type]
        max_prior_per_problem=int(args.max_prior_per_problem),
        min_mean_plddt=float(args.min_mean_plddt),
    )
    report_json.parent.mkdir(parents=True, exist_ok=True)
    report_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"[DONE] Wrote {out_config}")
    print(f"[DONE] Wrote {report_json}")
    for pid in ("1", "2", "3"):
        entry = payload.get(pid, {})
        if isinstance(entry, dict):
            print(
                f"[INFO] problem_{pid}: "
                f"sequence_prior_candidates={len(entry.get('sequence_prior_candidates', []))}, "
                f"rejected={len(entry.get('sequence_prior_rejected', []))}"
            )


def resolve_runtime_sources_config(
    root: Path | None = None,
    *,
    base_name: str = "processed_data/configs/submission_sources.json",
    out_name: str = "processed_data/configs/submission_sources_runtime.json",
    colab_name: str = "processed_data/colabfold",
    max_prior_per_problem: int = 8,
) -> Path:
    """Scan colabfold/ at predict time; prefer newest models (incl. predictions_msa_3m)."""
    root = root or _project_root()
    base = root / base_name
    if not base.is_file():
        return base
    colab = root / colab_name
    if not colab.is_dir() or not any(colab.rglob("*.pdb")):
        return base
    payload = build_sources(
        root=root,
        base_config=base,
        candidate_roots=[colab],
        prefer_sequence_prior=True,
        validate_candidates=True,
        max_length_delta=0,
        candidate_sort="mtime_desc",
        max_prior_per_problem=max_prior_per_problem,
        min_mean_plddt=50.0,
    )
    out = root / out_name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out


if __name__ == "__main__":
    main()
