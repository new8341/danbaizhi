# danbaizhi — 实验记录

> 新行由 `scripts/archive_competition.py` 自动追加。手工行请保持表格格式。

| 时间戳 | 分数 | commit | 假设/备注 | 结果 |
|--------|------|--------|-----------|------|
| 202606192106 | 0.717129 | 8a8ce02 | auto_prior max24 P1_3m 天池 2026-06-19 21:06:20 | guidang only (below cundang best) |
| 202606160717 | 0.717129 | 2977fa8 | MSA ColabFold 先验 + pLDDT≥50 | best（cundang） |
| 202605241146 | 0.717129 | — | 序列先验锁版 | guidang 基线 |
| 20260519 | 0.537492 | — | fast-preview 低 pLDDT | **失败** — 勿用 preview 冲榜 |
| 20260505 | 0.700463 | — | 全原子 mmCIF + hybrid | 格式跃迁 |

## 进行中

- **A1 extra models**：ColabFold `predictions_msa_3m/`（3 models × 3 recycles），WSL CPU 长跑

## 待验证

- [ ] extra models 完成后 → `build_sequence_prior_sources.py` → 更新 `submission_sources.json` → publish
