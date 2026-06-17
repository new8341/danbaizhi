# 任务 4 — Shenjingsuanzi（神经算子 PDE）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `shenjingsuanzi` |
| 输出 | `/saisresult/submission.zip`（`KS_pred_A.hdf5` + `cylinder_pred_A.hdf5`） |
| 输入 | `/saisdata/49/problem1`, `problem2`；训练数据 `/saisdata/48/` |
| 镜像仓库 | `.../ai4s-lee/shenjingsuanzi:<tag>` |
| 环境 | V100 16G，限时 6h；镜像建议 <5G |

## 当前状态

- Runner：`submit/tracks/shenjingsuanzi.py` → `submit/tracks/shenjingsuanzi_agent/`
- KS：挂载 `KS_train.hdf5` 时训练 FNO1d 并自回归预测 380 步；无训练集时用 test seed 外推；再失败则 sample 兜底
- Cylinder：调用挂载 `problem2/inference/run_inference.py`（FNO 权重）；失败则 sample 兜底
- 参考实现（本地）：`shenjingsuanzi/daima/202605192309`（初赛 ~57.69），未打入镜像

## 最后一周

Agent 代码在 `submit/tracks/shenjingsuanzi_agent/`，由 Dockerfile 随 `submit/` 一并 COPY。

## 环境变量

- `SHENJING_MODEL=fno`（problem2 推理模型）
- `SHENJING_KS_EPOCHS`（默认 24；6h 预算内可调大）
- `SHENJING_KS_PRESET=score-push`（默认；或 `balanced` / `SHENJING_QUICK=1` 冒烟）

## 本地验证

需自建 `saisdata/49/problem{1,2}/sample_submission/` 或使用评测挂载结构；见 `submit/tests/test_track_runners.py`。
