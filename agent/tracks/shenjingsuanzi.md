# 任务 4 — Shenjingsuanzi（神经算子 PDE）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `shenjingsuanzi` |
| 输出 | `/saisresult/submission.zip`（`KS_pred_A.hdf5` + `cylinder_pred_A.hdf5`） |
| 输入 | `/saisdata/49/problem1`, `problem2`；训练数据 `/saisdata/48/` |
| 镜像仓库 | `.../ai4s-lee/shenjingsuanzi:<tag>` |
| 环境 | V100 16G，限时 6h；镜像建议 <5G |

## 当前状态

- Runner：`submit/tracks/shenjingsuanzi.py`（KS 用 sample 兜底；problem2 可跑 FNO inference）  
- Baseline 推理：`documen/Shenjingsuanzi/problem2/inference/`（评测时以挂载为准）  

## 最后一周

须将 Agent 代码置于 `/app/agent_code/` 并附 README（可在 Dockerfile.shenjingsuanzi 中 COPY 业务目录）。

## 环境变量

- `SHENJING_MODEL=fno`（problem2 推理模型）

## 本地验证

需自建 `saisdata/49/problem{1,2}/sample_submission/` 或使用评测挂载结构；见 `submit/tests/test_track_runners.py`。
