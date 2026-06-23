# DrugCLIP Agent — 复赛镜像说明

## 1. 方案整体介绍与 Agent 工作流

DrugCLIP 虚拟筛选 Agent 自主遍历镜像内 benchmark（117 任务），对每个 task 的候选配体打分排序，输出 `result.csv` + `result.log`，打包为 `/saisresult/result.zip`。

阶段：`literature` → `diagnosis` → `strategy` → `inference` → `pack`（见 `result.log`）

## 2. 模型结构、建模思路与创新点

- **主策略**：`hybrid_max_qed_v2` — Morgan 指纹 Tanimoto + QED/口袋重原子 bonus 两阶段融合
- **可选神经**：`DRUGCLIP_STRATEGY=auto` 且权重+GPU 栈可用时 `neural_hybrid`（Uni-Mol DrugCLIP 检索）
- **禁止**：预置 `result.csv`、携带 active/inactive 标签、oracle 评测反馈调参

## 3. 数据来源与去泄漏

- **测试输入**：`documen/DrugClip/benchmark/` 打入镜像 `/app/benchmark/`（无标签）
- **禁止**：DUD-E/LIT-PCBA 标签、ChEMBL 反向构建答案库、HuggingFace 测试标签

## 4. 训练 / 推理 / 排序流程

1. `BenchmarkIndex` 遍历 manifest
2. `resolve_strategy()` 选择 hybrid 或 neural_hybrid
3. 并行 `score_task_*` 写 `result.csv`
4. `pack_submission` → `result.zip`

## 5. 环境依赖（Docker 默认 slim 构建）

| 包 | 用途 |
|----|------|
| rdkit, biopandas, numpy | 指纹与数据处理 |
| lmdb, tqdm, pyyaml | 神经路径（可选） |

代码：`/app/submit/tracks/drugclip_agent/`

## 6. 复现步骤

```bash
export DRUGCLIP_BENCHMARK_ROOT=/app/benchmark
sh /app/run.sh
```

## 7. 运行资源

| 项 | 估计 |
|----|------|
| GPU | 评测 V100；slim 镜像走 CPU hybrid |
| 时间 | 全 benchmark 约 10–30 min（`DRUGCLIP_WORKERS=8`） |
| 磁盘 | benchmark ~275MB |

## 8. API Key 与外部服务

| 项 | 环境变量 |
|----|----------|
| LLM API Key | `DRUGCLIP_LLM_API_KEY` |
| base_url | `DRUGCLIP_LLM_BASE_URL` |
| 模型 | `DRUGCLIP_LLM_MODEL` |

## 9. 随机种子

`DRUGCLIP_SEED`（默认 42）；RDKit 指纹确定性；多进程顺序可能略有浮动。

## 10. 目录

```
/app/benchmark/           测试输入（无标签）
/app/agent_code/          本 README + drugclip_agent 副本
/app/submit/              runner
/app/run.sh               评测入口
```
