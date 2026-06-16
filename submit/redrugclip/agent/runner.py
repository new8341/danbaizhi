"""
Autonomous DrugCLIP optimization agent.

Pipeline (per document/rull.md):
  1. Literature / baseline reproduction
  2. Bottleneck diagnosis on pilot tasks
  3. Strategy search (inference policies)
  4. Full benchmark inference + submission packaging
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager

import numpy as np
import yaml

from agent.logger import AgentLog
from agent.strategies import (
    PLATFORM_SCORE_HISTORY,
    Strategy,
    default_strategy_grid,
    strategy_to_config,
)
from src.benchmark import BenchmarkIndex, TaskInfo
from src.drugclip_runner import drugclip_available
from src.ef1 import load_labeled_tsv, mean_ef1_from_submission
from src.paths import OUTPUTS_DIR, PROJECT_ROOT
from src.submission import build_result_csv, package_result_zip
from src.validate_submit import validate_result_csv


def _pilot_separation_metric(scores: dict[str, float]) -> float:
    """Proxy when test labels unavailable: top 1% vs bottom 1% mean score gap."""
    if len(scores) < 100:
        return 0.0
    vals = np.array(sorted(scores.values()))
    k = max(1, len(vals) // 100)
    return float(vals[-k:].mean() - vals[:k].mean())


@contextmanager
def _agent_lock():
    lock = OUTPUTS_DIR / ".agent.lock"
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    if lock.exists():
        raise RuntimeError(
            f"Another agent run appears active (lock: {lock}). "
            "Stop other processes or remove the lock if stale."
        )
    lock.write_text(str(os.getpid()), encoding="utf-8")
    try:
        yield
    finally:
        if lock.exists():
            lock.unlink(missing_ok=True)


def _archive(note: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M")
    script = PROJECT_ROOT / "scripts" / "archive_run.py"
    subprocess.run(
        [sys.executable, str(script), "--stamp", stamp, "--note", note],
        cwd=str(PROJECT_ROOT),
        check=False,
    )
    return stamp


def _evaluate_strategy_on_tasks(
    strategy: Strategy,
    tasks: list[TaskInfo],
    index: BenchmarkIndex,
) -> tuple[float, dict[str, dict[str, float]]]:
    scorer, config = strategy_to_config(strategy)
    per_task: dict[str, dict[str, float]] = {}
    metrics: list[float] = []

    for task in tasks:
        rows = list(index.iter_ligand_rows(task))
        scores = scorer.score_task(task, rows, config)
        per_task[task.task_id] = scores
        metrics.append(_pilot_separation_metric(scores))

    return float(np.mean(metrics)), per_task


class DrugClipAgent:
    def __init__(self, config_path: Path | None = None):
        cfg_path = config_path or PROJECT_ROOT / "configs" / "agent.yaml"
        with cfg_path.open(encoding="utf-8") as f:
            self.cfg = yaml.safe_load(f)
        self.index = BenchmarkIndex()
        self.log = AgentLog(OUTPUTS_DIR / "result.log")
        self.experiment_db = OUTPUTS_DIR / "experiments.jsonl"

    def _log_experiment(self, record: dict) -> None:
        self.experiment_db.parent.mkdir(parents=True, exist_ok=True)
        with self.experiment_db.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

    def phase_literature_and_baseline(self) -> None:
        self.log.header("Phase 1: Literature parsing & baseline reproduction")
        self.log.block(
            "Reference: Science — Deep contrastive learning enables genome-wide virtual screening (DrugCLIP).\n"
            "Method: contrastive pocket–molecule embeddings, retrieval via dot product after L2 normalize.\n"
            "Pipeline: pocket = residues within 6Å of co-crystal ligand; ligand 3D conformers for LMDB.\n"
            "Competition constraint: document/benchmark is inference-only (no test labels for training).\n"
            "\nOptimization axes (rull.md):\n"
            "  - Inference: multi-FP ensemble (Morgan2/3, FCFP, MACCS), multi-receptor max/mean.\n"
            "  - Ranking: temperature sharpening for EF@1%, substructure & physchem vs co-crystal.\n"
            "  - Data: 6Å pocket from receptor+ref ligand; LIT-PCBA paired receptor-ligand structures.\n"
        )
        if drugclip_available():
            self.log.line("DrugCLIP checkpoint detected — full neural retrieval available.")
        else:
            self.log.line(
                "DrugCLIP weights not found under weights/ — agent uses fingerprint baseline "
                "aligned with co-crystal ligand (Tanimoto). Run scripts/download_weights.py for neural mode."
            )
        self.log.flush()

    def phase_diagnosis(self, pilot_tasks: list[TaskInfo]) -> None:
        self.log.header("Phase 2: Bottleneck diagnosis (pilot tasks + platform feedback)")
        for h in PLATFORM_SCORE_HISTORY:
            self.log.line(
                f"Platform {h['date']}: score={h['score']:.4f} strategy={h['strategy']}"
            )
        self.log.line(
            "Diagnosis: ensemble+physchem+sharpening hurt EF1% (11.29 vs 18.87). "
            "Revert to Morgan2 co-crystal similarity + light QED; conservative tweaks only."
        )
        champion = next(
            (s for s in default_strategy_grid() if s.name == "hybrid_max_qed"),
            default_strategy_grid()[0],
        )
        baseline, _ = _evaluate_strategy_on_tasks(champion, pilot_tasks, self.index)
        self.log.line(f"Pilot champion (hybrid_max_qed) separation metric: {baseline:.4f}")
        self.log.flush()

    def phase_strategy_search(
        self, pilot_tasks: list[TaskInfo]
    ) -> tuple[Strategy, dict]:
        self.log.header("Phase 3: Autonomous strategy search")
        strategies = [s for s in default_strategy_grid() if not s.rejected]
        proxy_path = PROJECT_ROOT / "data" / "proxy_labels.tsv"
        use_proxy = proxy_path.is_file()

        champion = next((s for s in strategies if s.name == "hybrid_max_qed"), strategies[0])
        best_strategy = champion
        best_score = -1e9
        results: dict = {}

        for s in strategies:
            metric, task_scores = _evaluate_strategy_on_tasks(s, pilot_tasks, self.index)
            ef1_proxy = None
            if use_proxy:
                labels = {k: v for k, v in load_labeled_tsv(proxy_path)}
                ef1s = []
                for tid, scores in task_scores.items():
                    ef1s.append(mean_ef1_from_submission(scores, labels))
                if ef1s:
                    ef1_proxy = float(np.mean(ef1s))
                    metric = ef1_proxy

            record = {
                "strategy": s.name,
                "metric": metric,
                "ef1_proxy": ef1_proxy,
                "description": s.description,
            }
            self._log_experiment(record)
            self.log.line(
                f"Strategy {s.name}: metric={metric:.4f} — {s.description}"
            )

            results[s.name] = record
            if metric > best_score:
                best_score = metric
                best_strategy = s

        # Never pick below champion unless pilot clearly improves; stay conservative
        champ_metric, _ = _evaluate_strategy_on_tasks(champion, pilot_tasks, self.index)
        if best_score < champ_metric * 1.02:
            best_strategy = champion
            best_score = champ_metric
            self.log.line(
                f"No pilot strategy beat champion by 2% margin; keeping {champion.name}."
            )

        self.log.line(f"Selected strategy: {best_strategy.name} (metric={best_score:.4f})")
        self.log.flush()
        return best_strategy, results

    def phase_full_inference(
        self,
        strategy: Strategy,
        task_filter: list[str] | None = None,
        resume_csv: Path | None = None,
        reuse_if_valid: bool = False,
    ) -> dict[str, dict[str, float]]:
        self.log.header("Phase 4: Full benchmark inference")
        scorer, config = strategy_to_config(strategy)
        tasks = self.index.tasks
        if task_filter:
            tasks = [t for t in tasks if t.task_id in task_filter]

        import csv as csv_mod

        done_tasks: set[str] = set()
        csv_path = OUTPUTS_DIR / "result.csv"
        if reuse_if_valid and not task_filter and csv_path.is_file():
            report = validate_result_csv(csv_path, self.index)
            if report.ok:
                self.log.line(
                    f"Reusing validated result.csv ({report.row_count} rows); "
                    f"strategy={strategy.name} (skip re-inference)."
                )
                self.log.flush()
                return {}
        if resume_csv and resume_csv.is_file():
            if not csv_path.is_file():
                import shutil

                shutil.copy2(resume_csv, csv_path)
            with csv_path.open(encoding="utf-8") as f:
                for row in csv_mod.DictReader(f):
                    done_tasks.add(row["task_id"])
        elif csv_path.is_file():
            try:
                csv_path.unlink()
            except PermissionError:
                csv_path = OUTPUTS_DIR / "result_new.csv"
                self.log.line(f"result.csv locked; writing to {csv_path.name}")
                self.log.flush()
        first_write = True
        all_scores: dict[str, dict[str, float]] = {}

        for i, task in enumerate(tasks, 1):
            if task.task_id in done_tasks:
                self.log.line(f"Skip completed task {task.task_id}")
                continue
            self.log.line(
                f"[{i}/{len(tasks)}] Scoring {task.task_id} ({task.num_ligands} ligands) "
                f"strategy={strategy.name}"
            )
            self.log.flush()
            rows = list(self.index.iter_ligand_rows(task))
            scores = scorer.score_task(task, rows, config)
            all_scores[task.task_id] = scores

            from src.submission import append_scores_csv

            append_scores_csv(
                csv_path,
                task.task_id,
                scores,
                write_header=first_write,
            )
            first_write = False

        if csv_path.name == "result_new.csv":
            final = OUTPUTS_DIR / "result.csv"
            if final.is_file():
                try:
                    final.unlink()
                except PermissionError:
                    pass
            if not final.is_file():
                csv_path.replace(final)
                csv_path = final

        self.log.line(f"Inference complete. CSV: {csv_path}")
        self.log.flush()
        return all_scores

    def phase_package(self) -> Path:
        self.log.header("Phase 5: Submission packaging")
        csv_path = OUTPUTS_DIR / "result.csv"
        log_path = OUTPUTS_DIR / "result.log"
        self.log.line("Validating and building result.zip")
        self.log.flush()

        zip_path = package_result_zip(csv_path, log_path)
        self.log.line(f"Created {zip_path}")
        self.log.flush()
        return zip_path

    def run(
        self,
        pilot_only: bool = False,
        tasks: list[str] | None = None,
        skip_archive: bool = False,
        fast: bool = False,
        forced_strategy: str | None = None,
        reuse_if_valid: bool = False,
    ) -> Path | None:
        with _agent_lock():
            return self._run_locked(
                pilot_only=pilot_only,
                tasks=tasks,
                skip_archive=skip_archive,
                fast=fast,
                forced_strategy=forced_strategy,
                reuse_if_valid=reuse_if_valid,
            )

    def _run_locked(
        self,
        pilot_only: bool = False,
        tasks: list[str] | None = None,
        skip_archive: bool = False,
        fast: bool = False,
        forced_strategy: str | None = None,
        reuse_if_valid: bool = False,
    ) -> Path | None:
        if not skip_archive:
            _archive("agent run start")

        from agent.strategies import default_strategy_grid

        pilot_ids = self.cfg.get("pilot_task_ids") or [
            "dude_ampc",
            "dude_ada",
            "dude_inha",
            "litpcba_ESR1_ago",
            "litpcba_PPARG",
        ]
        pilot_tasks = [self.index.get(tid) for tid in pilot_ids if tid in self.index.task_ids()]

        self.phase_literature_and_baseline()
        self.phase_diagnosis(pilot_tasks)
        strategies_map = {s.name: s for s in default_strategy_grid()}
        if forced_strategy:
            if forced_strategy not in strategies_map:
                raise ValueError(f"unknown strategy: {forced_strategy}")
            best = strategies_map[forced_strategy]
            self.log.header("Phase 3: Strategy selection (forced)")
            self.log.line(f"Using strategy: {best.name}")
            self.log.flush()
        elif fast:
            best = default_strategy_grid()[0]
            self.log.header("Phase 3: Strategy selection (--fast)")
            self.log.line(f"Using fixed strategy: {best.name}")
            self.log.flush()
        else:
            best, _search = self.phase_strategy_search(pilot_tasks)

        if pilot_only:
            self.log.line("pilot_only=True — skipping full inference.")
            self.log.flush()
            return None

        resume = None
        if forced_strategy is None and (OUTPUTS_DIR / "result.csv").is_file():
            resume = OUTPUTS_DIR / "result.csv"
        self.phase_full_inference(
            best,
            task_filter=tasks,
            resume_csv=resume,
            reuse_if_valid=reuse_if_valid,
        )
        if not skip_archive:
            _archive("agent run after full inference")

        zip_path = self.phase_package()

        if not skip_archive:
            _archive("agent run final submission")

        subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "scripts" / "prepare_submit.py")],
            cwd=str(PROJECT_ROOT),
        )

        subprocess.run(
            [
                sys.executable,
                str(PROJECT_ROOT / "scripts" / "validate_submission.py"),
                "--zip",
                str(zip_path),
            ],
            cwd=str(PROJECT_ROOT),
        )
        return zip_path
