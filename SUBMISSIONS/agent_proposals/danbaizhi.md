# 蛋白质构象系综 Agent 方案说明

**队伍**：new8341 / Fusai  
**赛道**：任务 3 — 蛋白质构象系综生成（danbaizhi）  
**文档版本**：复赛 2026-06

---

## 一、方案整体介绍

本 Agent 针对 **三条序列**（problem 1/2/3）生成 **构象系综**，输出多条全原子 mmCIF 预测结构，打包为 `/saisresult/submission.zip`。

**线上参考分**：**0.717129**（2026-05-24，ColabFold MSA 多模型先验 + 模板 hybrid 管线）。

Agent 五阶段（写入 `agent.log`）：

1. **理解**：读 `/saisdata/{1,2,3}.json` 序列与约束；
2. **假设**：序列条件先验（ColabFold `predictions_msa_3m`）优于纯模板；
3. **生成**：多构象采样 + 模板对齐 hybrid；
4. **验证**：几何自检（clash、RMSD 多样性）；
5. **提交**：mmCIF + 审计日志打包。

---

## 二、Agent 工作流程

```
/app/run.sh
    → submit/tracks/danbaizhi.py
        → 复制 saisdata/*.json → Project/data/
        → Project/code/main.py predict
            ├─ build_sequence_prior_sources（DANBAIZHI_AUTO_PRIOR=1）
            │     扫描 processed_data/colabfold/predictions_msa_3m
            ├─ generate_submission.py
            │     模板 + 序列先验 hybrid → mmCIF
            └─ agent.log 五阶段记录
        → 解压至 staging → submission.zip
    → /saisresult/submission.zip
```

---

## 三、模型结构与建模思路

### 3.1 序列条件先验（核心涨分来源）

| 项 | 说明 |
|----|------|
| 来源 | ColabFold AlphaFold2（MSA 模式，3 models × 3 recycles） |
| 路径 | `Project/processed_data/colabfold/problem_{N}/predictions_msa_3m/` |
| 门槛 | mean pLDDT ≥ 50 才合入先验（防低质量预览结构） |
| 上限 | `max_prior_per_problem=24`，按 mtime 优先 |

**经验**：涨分来自 **高质量多样构象**，非局部 JSON 调参；无合格 ColabFold 输出时回退模板基线。

### 3.2 模板 hybrid 管线

- 公开 PDB 模板检索与对齐；
- 每题输出 `conf1..confN` 条 mmCIF（题 3 为 3 构象，题 1/2 为 4 构象）；
- 随机种子 **42**（`template_align` 扰动可复现）。

### 3.3 物理与几何

- OpenMM / mdtraj 用于局部几何与打包校验；
- 提交约束：≤100MB、全原子、无 NaN/Inf。

---

## 四、数据处理流程

| 步骤 | 说明 |
|------|------|
| 输入 | `/saisdata/1.json`、`2.json`、`3.json` |
| 先验构建 | 运行时扫描 colabfold 目录（**不打入镜像**） |
| 输出 | `{id}_conf{j}_pred.cif` + `agent.log` |
| 打包 | `submission.zip` → `/saisresult/` |

**禁止**：预置 mmCIF 答案、从固定构象库复制、硬编码测试序列。

---

## 五、环境依赖

| 组件 | 说明 |
|------|------|
| Python | 3.10-slim |
| numpy, mdtraj, openmm | 预测与几何 |
| 业务代码 | `/app/Project/code/` |
| Agent 配置 | `/app/Project/agent/` |

离线 ColabFold（开发机 WSL，非镜像内）：

- `Project/scripts/colabfold_wsl_env.ps1`
- 权重缓存：`Project/data/colabfold_xdg_cache`

---

## 六、复现步骤

### 6.1 评测容器

```bash
export FUSAI_TRACK=danbaizhi
export DANBAIZHI_AUTO_PRIOR=1
sh /app/run.sh
```

### 6.2 本地完整链

```powershell
cd Project
pip install -r code/requirements.txt
python code/main.py predict
python code/main.py verify-repro   # 与 checkpoint/golden 比对
```

Docker runner：

```powershell
py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi `
  --saisresult submit/_local_saisresult --work-dir H:\Fusai
```

---

## 七、API Key 与外部服务

| 变量 | 说明 |
|------|------|
| `DANBAIZHI_LLM_API_KEY` | Agent 规划/文献辅助（Cursor IDE Agent） |
| `DANBAIZHI_LLM_BASE_URL` | API 基址 |

配置：`/app/Project/agent/config.md`、`submit/Dockerfile.danbaizhi` ENV。  
出分后可停用；审核老师替换为自己的 Key。

**LLM 供应商**：OpenAI 兼容 API（开发阶段使用 Cursor Agent）。

---

## 八、输出规范

`submission.zip` 须含：

```
1_conf1_pred.cif … 1_conf4_pred.cif
2_conf1_pred.cif … 2_conf4_pred.cif
3_conf1_pred.cif … 3_conf3_pred.cif
agent.log
```

---

## 九、创新点与经验总结

1. **序列条件多模型先验**：ColabFold MSA 3m 构象显著提升系综质量；
2. **自动先验合并** `DANBAIZHI_AUTO_PRIOR=1`：无需手工改 JSON；
3. **pLDDT 门槛**：拒绝 fast-preview 低分结构，避免线上暴跌；
4. **Windows+WSL+ColabFold 基础设施**：可复用于后续多模型补跑。

---

## 十、合规声明

- 结果由 Agent 在容器内 **实时生成**；
- 镜像含推理代码与说明，**不含**预计算 submission；
- `agent.log` 记录完整研发阶段，满足审核要求。

---

## 十一、代码索引

| 路径 | 职责 |
|------|------|
| `Project/code/generate_submission.py` | mmCIF 生成与打包 |
| `Project/code/build_sequence_prior_sources.py` | ColabFold 先验合并 |
| `Project/code/main.py` | 入口 predict/verify-repro |
| `submit/tracks/danbaizhi.py` | Docker runner |
| `TASKS/danbaizhi/SUBMISSION_SPEC.md` | 提交规范 |
