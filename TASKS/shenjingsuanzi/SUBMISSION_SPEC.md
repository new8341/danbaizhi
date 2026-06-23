# shenjingsuanzi — 提交规范（复赛 2026-06）

## Docker

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `shenjingsuanzi` |
| Dockerfile | `submit/Dockerfile.shenjingsuanzi` |
| 镜像 | `.../ai4s-lee/shenjingsuanzi:0.1` |
| 入口 | `/app/run.sh`（唯一） |
| 代码审核 | `/app/agent_code/README.md` + `shenjingsuanzi_agent/` |

## 输出（强制）

`/saisresult/submission.zip` 须含 **四个** HDF5：

| 文件 | 说明 |
|------|------|
| `KS_pred_A.hdf5` | 第一题 A 榜 |
| `cylinder_pred_A.hdf5` | 第二题 A 榜 |
| `KS_pred_B.hdf5` | 第一题 B 榜 |
| `cylinder_pred_B.hdf5` | 第二题 B 榜 |

### 0 分条件（单题独立）

- zip 缺少对应 `KS_pred*.hdf5` 或 `cylinder_pred*.hdf5`
- HDF5 无 `tensor` 字段
- `tensor` shape 与测试集 N 不一致
- IC 检验：前 20 步最大绝对误差 > **5e-3**

## 数据挂载

```
/saisdata/49/problem1/data/   KS_train, KS_val, KS_test_A
/saisdata/49/problem2/        inference, models, cylinder_test_A
/saisdata/66/                 KS_test_B, cylinder_test_B（B榜）
/saisdata/48/problem2/data/train/  cylinder 训练（可选）
```

## 镜像允许 / 禁止

| 允许 | 禁止 |
|------|------|
| Agent 运行环境、/app/agent_code | 数据集打包 |
| PDE 知识库、Skill、MCP | 预计算预测 HDF5 |
| Agent 运行时训练逻辑 | 独立离线训练脚本目录 |
| 通用方法经验文档 | 针对性本题超参/方法泄露 |

## 代码审核时间线

- **6/26 14:00** 镜像截止；组委会拉取历史最优镜像审查
- **6/26–6/28 14:00** 前 20 名须代码提交入口交 Agent 方案说明

## 发布

```powershell
.\submit\publish_track.ps1 -Track shenjingsuanzi
```

## 实现

`submit/tracks/shenjingsuanzi_agent/` — `pipeline.py` 强制四文件输出
