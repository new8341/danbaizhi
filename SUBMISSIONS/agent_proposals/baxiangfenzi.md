# 靶向分子设计赛道 Agent 方案说明

**队伍**：new8341 / Fusai  
**赛道**：任务 2 — 靶向分子设计（baxiangfenzi）  
**文档版本**：复赛 2026-06

---

## 一、方案整体介绍

本 Agent 面向 **三靶点（target1/2/3.pdb）** 的靶向小分子设计任务，在容器内自主完成：

**口袋分析 → 候选生成 → AutoDock Vina 对接 → 逆合成路线规划 → 输出合成路径**

每个靶点独立运行一轮 Agent 循环，最终打包为 `/saisresult/result.zip`（`result1/2/3.csv`）。

**设计原则**：

- 结果必须在容器运行期间 **实时生成**，非预置分子库筛选；
- B 榜靶点文件路径不变（`/saisdata/37/target*.pdb`），内容替换后 Agent 自动重算；
- 输出不得与 A 榜完全相同（避免硬编码作弊）。

**当前成绩**：A 榜约 **0.6696**（Sprint1 对接+逆合成复合策略）。

---

## 二、Agent 工作流程

```
/app/run.sh
    → baxiangfenzi_agent/pipeline.py
        对每个 slot (1,2,3):
            ├─ analyze_target：从 PDB 估计 binding site 与 docking box
            ├─ generate_candidates：BRICS/规则片段枚举候选 SMILES
            ├─ dock：Vina 对接（失败时 pseudo_dock 启发式）
            ├─ select：分子分 + 路线分 官方复合加权
            └─ retrosyn：BRICS 逆合成路线验证
        → result{N}.csv（SMILES + 合成步骤）
    → /saisresult/result.zip
```

日志标记：`[agent] phase=init|analyze_target|generate_candidates|dock|select|retrosyn|done`

---

## 三、模型结构与建模思路

### 3.1 靶点分析

- 解析 PDB 原子坐标，估计口袋中心与 box 尺寸（`targets.binding_site_from_pdb`）；
- 支持多链复合物；box 用于 Vina `--center_x/y/z`、`--size_x/y/z`。

### 3.2 候选生成

- 基于 BRICS 片段与药物化学规则枚举 SMILES；
- 预算：`BAXIANG_MAX_CANDIDATES`（默认 200）、`BAXIANG_MAX_DOCK`（默认 60）。

### 3.3 对接评分

- **AutoDock Vina** 亲和力（kcal/mol，越负越好）；
- 受体预处理：Open Babel 转 PDBQT，结果缓存于临时工作目录；
- Vina 不可用时降级 `pseudo_dock_score` 几何启发式（日志标注）。

### 3.4 选择与逆合成

- **分子分** `score_molecule`：Vina + SA score（合成可达性）；
- **路线分** `score_route`：BRICS 逆合成步骤验证；
- **复合分** `official_composite`：官方加权（分子:路线 = **6:4**，复赛口径）；
- 在 top pool（`BAXIANG_SELECT_POOL=15`）中选最优可合成路线。

---

## 四、数据处理流程

| 阶段 | 输入 | 输出 |
|------|------|------|
| 读靶点 | `/saisdata/37/target{N}.pdb` | binding site 几何 |
| 生成 | 靶点特征 | 候选 SMILES 列表 |
| 对接 | 候选 + 受体 PDBQT | 亲和力排序 |
| 输出 | 最优分子+路线 | `result{N}.csv` |

**禁止**：镜像内预置答案表、从固定分子库抽取、硬编码 A 榜结果。

---

## 五、环境依赖

| 组件 | 说明 |
|------|------|
| Python | 3.10-slim |
| RDKit | 分子处理、SA score |
| AutoDock Vina | `apt autodock-vina` |
| Open Babel | `apt openbabel` |

代码：

- `/app/submit/tracks/baxiangfenzi_agent/`
- 审核：`/app/Code/README.md`、`/app/Code/main.py`

---

## 六、复现步骤

```bash
export FUSAI_TRACK=baxiangfenzi
export SAISDATA=/saisdata
export SAISRESULT=/saisresult
sh /app/run.sh
```

本地：

```powershell
py -3 submit/main.py --track baxiangfenzi \
  --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir H:\Fusai
```

---

## 七、API Key 与外部服务

复赛要求镜像内包含 API Key 配置位（出分后可停用）：

| 变量 | 用途 |
|------|------|
| `BAXIANG_LLM_API_KEY` | LLM 辅助分子设计/路线反思（可选增强） |
| `BAXIANG_LLM_BASE_URL` | API 基址（OpenAI 兼容） |
| `BAXIANG_LLM_MODEL` | 模型名 |

**配置位置**：`submit/Dockerfile.baxiangfenzi` ENV；审核老师可替换为自己的 Key。

当前核心链路 **不强制依赖 LLM**，对接+逆合成为主路径。

---

## 八、B 榜说明

- 路径：`/saisdata/37/target1.pdb`、`target2.pdb`、`target3.pdb`（**文件名不变**）；
- Agent 每次启动重新读 PDB、重算口袋与对接，自然产生与 A 榜不同的结果；
- 提交前应在全新容器验证，确保无本地路径依赖。

---

## 九、创新点

1. **口袋自适应 box**：无需人工指定对接中心；
2. **对接+逆合成双阶段复合**：兼顾结合能与可合成性；
3. **多级降级**：Vina → pseudo dock → 默认片段，保证工程稳定性。

---

## 十、代码索引

| 文件 | 职责 |
|------|------|
| `pipeline.py` | 三靶点编排 |
| `candidates.py` | 候选枚举 |
| `docking.py` | Vina 对接 |
| `retrosyn.py` | 逆合成与复合分 |
| `TASKS/baxiangfenzi/SUBMISSION_SPEC.md` | 提交规范 |
