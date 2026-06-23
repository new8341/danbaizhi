# Danbaizhi Agent — 复赛镜像说明

## 1. 方案整体介绍

蛋白质构象系综生成 Agent：读取 `/saisdata/{1,2,3}.json`，经序列条件多模型先验（ColabFold MSA 构象）+ 模板 hybrid 管线生成多样 mmCIF，打包为 `submission.zip`。入口 `/app/run.sh`。

## 2. 模型结构与建模思路

- **先验**：`DANBAIZHI_AUTO_PRIOR=1` 扫描 `Project/processed_data/colabfold` 下 `predictions_msa_3m` 等多模型输出
- **系综**：每题输出多构象 mmCIF（`{id}_conf{N}_pred.cif`）
- **物理**：OpenMM/mdtraj 用于局部几何与打包校验

## 3. 数据处理流程

1. `danbaizhi.py` 将 `/saisdata/*.json` 复制到 `Project/data/`
2. `Project/code/main.py predict` 生成 `Project/result/`
3. 提取 mmCIF + `agent.log` → `/saisresult/submission.zip`

## 4. 环境依赖

| 组件 | 说明 |
|------|------|
| Python 3.10 | slim 基础镜像 |
| numpy, mdtraj, openmm | pip / apt |
| 业务代码 | `/app/Project/code/` |

## 5. 复现步骤

```bash
sh /app/run.sh
# 或
python3 /app/submit/main.py --track danbaizhi \
  --saisdata /saisdata --saisresult /saisresult --work-dir /app
```

## 6. API Key 配置

| 项 | 位置 |
|----|------|
| 环境变量 | `DANBAIZHI_LLM_API_KEY` |
| base_url | `DANBAIZHI_LLM_BASE_URL` |
| 说明文档 | `/app/Project/agent/config.md` |

## 7. 输出规范

`/saisresult/submission.zip` 须含：

- `1_conf*_pred.cif` … `3_conf*_pred.cif`（全原子 mmCIF）
- `agent.log`（五阶段审计日志）

约束：≤100MB；无 NaN/Inf。

## 8. 镜像目录

```
/app/Project/       主业务与 agent 配置
/app/submit/        Docker runner
/app/agent_code/    本 README（代码审核）
/app/run.sh         评测入口
```
