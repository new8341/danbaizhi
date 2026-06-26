# checkpoint

| Path | Role |
|------|------|
| `submission_sources.json` | Frozen per-problem strategy (0.717129 run); paths relative to `Project/` |
| `golden/` | Authoritative mmCIF + `agent.log` + `output.zip` from online submission |

**P2**：`processed_data/configs/submission_sources.json` 中 `golden_conformer_cifs` 指向本目录 `golden/2_conf*_pred.cif`（预测时复制，不重新跑 mdtraj）。

**P1/P3**：由 `code/generate_submission.py` 按 `seed=42` 生成；`golden/output.zip` 供 `python code/main.py verify-repro` 比对。

ColabFold 权重（约 3.5 GB）未打包；详见 `../README.md`。
