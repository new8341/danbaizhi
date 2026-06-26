# shenjingsuanzi — 需求摘要

## 任务

神经算子 PDE：Problem1 KS 方程 + Problem2 圆柱绕流。

## 输入

- `/saisdata/49/problem1`, `problem2`
- 训练：`/saisdata/48/`（含 `KS_train.hdf5`）

## 输出

`submission.zip`：`KS_pred_A.hdf5`, `cylinder_pred_A.hdf5`

## 环境

V100 16G，限时 6h；镜像建议 <5G

## 复赛要点（readme §复赛评测提交规范）

- **A+B 四文件** zip 提交
- B 榜测试：`/saisdata/66/KS_test_B.hdf5`、`cylinder_test_B.hdf5`
- KS 测试不提供 λ₂，须仅凭 20 步观测预测
- 6h 时限；禁止公开预训练权重（须本题训练集从头训）
- IC 容差 5e-3
