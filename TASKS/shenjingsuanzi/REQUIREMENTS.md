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

## 参考

初赛参考 pipeline ~**57.69**（`shenjingsuanzi/daima/202605192309`）
