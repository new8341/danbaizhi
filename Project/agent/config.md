# Agent config

| Item | Value |
|------|--------|
| Platform | Cursor IDE Agent |
| Task | 蛋白质构象系综生成（`document/rull.md`） |
| Online score | **0.717129** (2026-05-24) |

## Scripts (relative to `Project/`)

| 阶段 | 命令 |
|------|------|
| 预测 | `python code/main.py` |
| 先验合并（可选） | `python code/main.py build-prior` |
| 自检 | `python code/main.py verify-repro` |

## Tools

- `code/generate_submission.py` — 构象生成与打包
- `code/build_sequence_prior_sources.py` — ColabFold 先验合并（离线）
- `code/run_colabfold_optional.py` — 可选 ColabFold 批量（本包未在审核路径执行）
- 公开 RCSB 模板：`processed_data/public/`

## Reproducibility

- 随机种子 **42**（`template_align` 扰动与多样性子采样）
- 权威参考：`checkpoint/golden/output.zip`
- 审核：`python code/main.py` 后 `verify-repro` 应通过
