# Baxiangfenzi Agent — 复赛镜像说明

## 1. 方案整体介绍

本 Agent 针对三个靶点（`target1/2/3.pdb`）自主完成：口袋分析 → 候选分子生成/枚举 → AutoDock Vina 对接 → 逆合成可行性筛选 → 输出 `result1/2/3.csv`。全流程由 `/app/run.sh` 启动，无需人工干预。

## 2. 模型结构与建模思路

- **对接**：Vina score 为主排序信号；口袋 box 由 PDB 几何自动估计
- **候选**：BRICS 片段组合 + 规则过滤（分子量、可合成性启发式）
- **逆合成**：`retrosyn` 模块对 top 候选做合成可达性评估
- **B 榜**：输入仍为 `/saisdata/37/target{1,2,3}.pdb`，文件名不变、内容替换；**不得**输出与 A 榜完全相同的结果

## 3. 数据处理流程

1. 读取 `/saisdata/37/target*.pdb`
2. 每靶点生成候选池（`BAXIANG_MAX_CANDIDATES` 等环境变量控制预算）
3. Vina 对接 + 逆合成筛选
4. 写入 staging → 打包 `/saisresult/result.zip`

## 4. 环境依赖

| 组件 | 版本/来源 |
|------|-----------|
| Python | 3.10（`python:3.10-slim`） |
| RDKit | pip |
| AutoDock Vina | apt `autodock-vina` |
| Open Babel | apt `openbabel` |

业务代码：`/app/submit/tracks/baxiangfenzi_agent/`

## 5. 复现步骤

```bash
# 容器内（评测环境）
sh /app/run.sh

# 本地
export FUSAI_TRACK=baxiangfenzi
python3 /app/submit/main.py --track baxiangfenzi \
  --saisdata /saisdata --saisresult /saisresult --work-dir /app
```

## 6. API Key 配置

| 项 | 位置 |
|----|------|
| 环境变量 | `BAXIANG_LLM_API_KEY`（可在 Dockerfile ENV 或 `submit/tracks/baxiangfenzi_agent/` 读取） |
| 供应商 / base_url | `BAXIANG_LLM_BASE_URL`（默认 OpenAI 兼容接口） |
| 模型名 | `BAXIANG_LLM_MODEL` |

> 出分后可停用 Key；审核老师请替换为自己的 Key 复现。

## 7. 目录结构（复赛要求）

```
/app/Code/          ← 本 README、main.py
/app/Reference/     ← 参考文献
/app/submit/        ← 统一 runner + baxiangfenzi_agent
/app/run.sh         ← 唯一评测入口
```
