# shenjingsuanzi — 提交规范（复赛）

## Docker

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `shenjingsuanzi` |
| Dockerfile | `submit/Dockerfile.shenjingsuanzi` |
| 镜像 | `.../ai4s-lee/shenjingsuanzi:0.1` |
| 入口 | `/app/run.sh` |
| Agent 代码审核 | `/app/agent_code/` + `README.md` |

## 输出（复赛 2026-06 更新）

`/saisresult/submission.zip` 须含 **四个** 文件：

| 文件 | 说明 |
|------|------|
| `KS_pred_A.hdf5` | 第一题 A 榜 |
| `cylinder_pred_A.hdf5` | 第二题 A 榜 |
| `KS_pred_B.hdf5` | 第一题 B 榜 |
| `cylinder_pred_B.hdf5` | 第二题 B 榜 |

缺任一文件 → **该题 0 分**（另一题仍计分）。

## 数据挂载

```
/saisdata/49/problem1/data/   KS_train, KS_val, KS_test_A
/saisdata/49/problem2/        inference, models, cylinder_test_A
/saisdata/66/                 KS_test_B, cylinder_test_B  (B榜)
/saisdata/48/problem2/data/train/  cylinder 训练集
```

## IC 一致性

前 20 步与测试输入一致，最大绝对误差 ≤ **5e-3**。

## 镜像禁止包含

- 数据集、预计算预测、**独立训练脚本**（Agent 运行时训练属 Agent 逻辑）
- 针对性过强的调参先验文档

## 发布

```powershell
.\submit\publish_track.ps1 -Track shenjingsuanzi
```

## 代码

`submit/tracks/shenjingsuanzi_agent/`
