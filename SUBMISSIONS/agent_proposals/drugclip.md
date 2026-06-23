# DrugCLIP 虚拟筛选 Agent 方案说明

**队伍**：new8341 / Fusai  
**赛道**：任务 1 — DrugCLIP 高通量虚拟筛选（drugclip）  
**文档版本**：复赛 2026-06

---

## 一、方案整体介绍

本 Agent 实现 **DUD-E / LIT-PCBA 风格 benchmark** 上的大规模虚拟筛选，自主完成：

**读 manifest → 策略决策 → 逐 task 打分排序 → 写 result.csv / result.log → 打包 result.zip**

评测指标：**Mean EF1%**（早期富集因子）。

**历史成绩**：**19.229531**（`hybrid_max_qed_v2` 指纹混合策略，2026-05-25）。

Agent 闭环阶段（写入 `result.log`）：

`literature` → `diagnosis` → `strategy` → `inference` → `pack`

---

## 二、Agent 工作流程

```
/app/run.sh
    → drugclip_agent/pipeline.py
        ├─ 加载 /app/benchmark/manifest.jsonl（117 tasks，无标签）
        ├─ resolve_strategy()
        │     ├─ neural_hybrid（权重+GPU+DrugCLIP 栈可用）
        │     └─ hybrid_max_qed_v2（默认 ACR 镜像）
        ├─ 并行 ProcessPoolExecutor 逐 task 推理
        └─ 写 result.csv + result.log
    → /saisresult/result.zip
```

---

## 三、模型结构、建模思路与创新点

### 3.1 主策略：hybrid_max_qed_v2（生产默认）

两阶段融合（对齐 ReDrugClip 冠军配置）：

| 阶段 | 信号 |
|------|------|
| 指纹相似 | Morgan2 Tanimoto vs 参考配体（radius=2, 2048 bits） |
| Hybrid bonus | QED 药物相似性 + 口袋重原子数启发式 |

关键超参（`scoring.HybridConfig`）：

- `qed_bonus=0.04`
- `pocket_heavy_bonus=0.02`
- `smiles_sim_weight=0.08`

### 3.2 可选策略：neural_hybrid

当镜像内含 DrugCLIP 权重与 Uni-Core 栈时：

1. 构建 LMDB（分子 + 口袋）；
2. 调用 `DrugCLIP/unimol/retrieval.py` 神经检索；
3. 与 hybrid 分按 `DRUGCLIP_NEURAL_BLEND`（默认 0.9）融合。

> ACR 个人版当前使用 slim 镜像（无 PyTorch），运行时自动降级 hybrid。

### 3.3 创新点

- **Native agent** 替代 vendored ReDrugClip，单仓库四赛道统一 runner；
- **策略自动切换** `DRUGCLIP_STRATEGY=auto`；
- **并行 task 推理**，可配置 `DRUGCLIP_WORKERS`；
- **完整审计日志**，满足复赛「可核验过程记录」要求。

---

## 四、数据来源与去泄漏

| 项 | 处理 |
|----|------|
| 测试输入 | `documen/DrugClip/benchmark/` → 镜像 `/app/benchmark/` |
| 标签 | **不打包** active/inactive |
| 禁止 | DUD-E/LIT-PCBA 官网标签、HF 标签集、ChEMBL 反向答案库 |
| 禁止 | 预置 `result.csv`、oracle 评测反馈调参 |

允许使用测试集之外的 **通用** 预训练能力，但不得以任何方式恢复测试标签。

---

## 五、训练 / 推理 / 排序流程

1. `BenchmarkIndex` 解析 task（受体、配体表、参考配体）；
2. 对每个 task 的所有 candidate ligands 打分；
3. CSV 列：`task_id, ligand_id, score`（降序即排名）；
4. `result.log` 记录策略、每 task 分数区间、平台历史。

**无容器内训练**（复赛 slim 镜像）；神经权重为推理 checkpoint（若启用）。

---

## 六、环境依赖

| 组件 | slim 镜像（ACR） | 神经扩展 |
|------|------------------|----------|
| Python | 3.10 | + PyTorch 2.1 |
| rdkit, biopandas | ✓ | ✓ |
| lmdb, pyyaml | ✓ | ✓ |
| Uni-Core, DrugCLIP | — | git clone @ build |

---

## 七、复现步骤

```bash
export DRUGCLIP_BENCHMARK_ROOT=/app/benchmark
export FUSAI_TRACK=drugclip
sh /app/run.sh
```

本地 mini：

```powershell
$env:DRUGCLIP_BENCHMARK_ROOT="submit/tests/fixtures/drugclip_mini"
$env:DRUGCLIP_MAX_TASKS="1"
py -3 submit/main.py --track drugclip --saisdata documen/DrugClip `
  --saisresult submit/_local_saisresult --work-dir H:\Fusai
```

---

## 八、运行资源

| 项 | 估计 |
|----|------|
| CPU | 8 workers 并行 |
| 全 benchmark | 约 10–30 min（hybrid） |
| 磁盘 | benchmark ~275MB |
| GPU | 神经路径需 V100；hybrid 仅需 CPU |

---

## 九、API Key 与外部服务

| 变量 | 说明 |
|------|------|
| `DRUGCLIP_LLM_API_KEY` | LLM 辅助策略/文献（可选） |
| `DRUGCLIP_LLM_BASE_URL` | API 基址 |
| `DRUGCLIP_LLM_MODEL` | 模型名 |

配置：`submit/Dockerfile.drugclip` ENV；审核时可替换。

---

## 十、随机种子与复现差异

- `DRUGCLIP_SEED=42`（若设置）；
- RDKit Morgan 指纹确定性；
- 多进程 task 顺序可能导致 log 行序差异，**不影响 CSV 分数**。

---

## 十一、合规声明

已落实复赛禁止项检查：

- 无预置 result；
- 无测试标签文件；
- `result.log` 完整保留 Agent 阶段；
- benchmark 仅含赛方提供的无标签输入。

---

## 十二、代码索引

| 路径 | 职责 |
|------|------|
| `submit/tracks/drugclip_agent/pipeline.py` | Agent 主编排 |
| `submit/tracks/drugclip_agent/scoring.py` | hybrid_max_qed_v2 |
| `submit/tracks/drugclip_agent/neural.py` | 神经检索 |
| `submit/tracks/drugclip_agent/benchmark.py` | manifest 解析 |
| `TASKS/drugclip/SUBMISSION_SPEC.md` | 提交规范 |
