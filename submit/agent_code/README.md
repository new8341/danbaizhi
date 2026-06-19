# Shenjingsuanzi Agent Code（复赛代码审核）

## 目录

| 路径 | 说明 |
|------|------|
| `/app/submit/tracks/shenjingsuanzi_agent/` | KS FNO1d + cylinder 推理 Agent |
| `/app/agent/` | 四赛道共享约定与日志规范 |
| `/app/submit/main.py` | 统一 runner 入口 |

## 运行数据（容器挂载，禁止打入镜像）

- `/saisdata/49/problem1/data/` — KS_train、KS_val、KS_test_A
- `/saisdata/49/problem2/` — cylinder 推理脚本与 FNO 权重（`models/`）
- `/saisdata/48/problem2/data/train/` — cylinder 训练集（可选）
- `/saisdata/66/` — **B 榜** `KS_test_B.hdf5`、`cylinder_test_B.hdf5`

## 输出（复赛规范）

`/saisresult/submission.zip` 须含 **四个** HDF5：

- `KS_pred_A.hdf5`、`cylinder_pred_A.hdf5`
- `KS_pred_B.hdf5`、`cylinder_pred_B.hdf5`

IC 一致性：输出前 20 步与测试输入一致（容差 5e-3）。

## 环境

- V100 16G，限时 6h
- `SHENJING_KS_PRESET=ks-q1`，`SHENJING_KS_EPOCHS=28`
- `SHENJING_MODEL=fno`（problem2）

## 入口

`/app/run.sh` → `FUSAI_TRACK=shenjingsuanzi`
