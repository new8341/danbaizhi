# Shenjingsuanzi Agent — 复赛镜像说明

## 1. 方案整体介绍

PDE 求解 Agent：两道题（KS 方程 + cylinder 绕流），A/B 双榜。容器启动后 `/app/run.sh` 唯一入口，实时推理生成四个 HDF5，打包 `/saisresult/submission.zip`。

## 2. Agent 代码位置

| 路径 | 说明 |
|------|------|
| `/app/submit/tracks/shenjingsuanzi_agent/` | KS FNO1d + cylinder FNO 推理 |
| `/app/agent_code/shenjingsuanzi_agent/` | 代码审核副本（与上同内容） |
| `/app/agent/` | 四赛道共享约定 |

## 3. 运行数据（挂载，禁止打入镜像）

```
/saisdata/49/problem1/data/     KS_train, KS_val, KS_test_A
/saisdata/49/problem2/          cylinder 推理脚本、FNO 权重 models/
/saisdata/66/                   B榜 KS_test_B.hdf5, cylinder_test_B.hdf5
/saisdata/48/problem2/data/train/  cylinder 训练集（可选）
```

## 4. 输出（复赛强制）

`/saisresult/submission.zip` **必须**含四个文件：

| 文件 | 说明 |
|------|------|
| `KS_pred_A.hdf5` | 第一题 A 榜 |
| `cylinder_pred_A.hdf5` | 第二题 A 榜 |
| `KS_pred_B.hdf5` | 第一题 B 榜 |
| `cylinder_pred_B.hdf5` | 第二题 B 榜 |

缺任一 → **该题 0 分**（另一题仍计分）。

### HDF5 校验

- 须含 `tensor` 字段，shape 与测试集 N 一致
- **IC 一致性**：前 20 步与输入最大绝对误差 ≤ **5e-3**

## 5. 镜像禁止包含

- 训练集/验证集文件（由平台挂载）
- **独立离线训练脚本**（Agent 运行时训练属 Agent 逻辑，可保留）
- 预计算预测 HDF5
- 针对性过强的调参先验（应写方法适用域与排错经验，而非本题超参）

## 6. 环境与资源

- GPU V100 16G，限时 6h
- `SHENJING_KS_PRESET=ks-q1`，`SHENJING_KS_EPOCHS=28`
- `SHENJING_MODEL=fno`（cylinder）

## 7. 入口

```bash
sh /app/run.sh   # FUSAI_TRACK=shenjingsuanzi
```

## 8. 方法经验（通用先验，非本题泄露）

- FNO 对周期边界 KS 较稳；长时 rollout 误差累积时需缩短 windows 或加强 IC 对齐
- cylinder 挂载权重推理快；容器内 finetune 需预留时间预算
- KS 训练过重会导致 6h 内 rollout 不足 — 宜轻量化 preset

## 9. 代码提交窗口

6/26 14:00 — 6/28 14:00：排行榜前 20 须另交 Agent 方案说明（word/md/pdf/ppt）。
