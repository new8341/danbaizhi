# 神经算子赛道 Agent 方案说明

**队伍**：new8341 / Fusai  
**赛道**：任务 4 — 神经算子（shenjingsuanzi）  
**文档版本**：复赛 2026-06

---

## 一、方案整体介绍

本方案构建了一个面向 **偏微分方程（PDE）时序预测** 的自主 Agent，在固定 Docker 入口 `/app/run.sh` 下完成：

1. **理解**：解析挂载数据目录，识别 KS 方程（problem1）与 cylinder 绕流（problem2）的 A/B 双榜测试文件；
2. **假设**：KS 采用 FNO1d 自回归 rollout；cylinder 采用挂载 FNO 权重推理；
3. **演进**：KS 在容器内按预算进行可选训练后推理；cylinder 优先调用 `/saisdata` 预置权重；
4. **验证**：强制产出四个 HDF5，校验文件存在性与 IC 一致性约束。

**复赛输出**：`/saisresult/submission.zip`，内含 `KS_pred_A/B.hdf5` 与 `cylinder_pred_A/B.hdf5`。

**历史成绩**：A 榜综合约 **81.78**（B 榜文件补齐后）；cylinder A 约 39.7，KS 各约 1.0+（持续优化中）。

---

## 二、Agent 工作流程

```
/app/run.sh
    → submit/main.py (FUSAI_TRACK=shenjingsuanzi)
        → shenjingsuanzi_agent/pipeline.run_agent()
            ├─ literature / diagnosis（平台历史与策略日志）
            ├─ KS board A：train(optional) + FNO1d rollout → KS_pred_A.hdf5
            ├─ KS board B：复用训练状态 → KS_pred_B.hdf5
            ├─ cylinder board A：FNO inference → cylinder_pred_A.hdf5
            └─ cylinder board B：FNO inference → cylinder_pred_B.hdf5
        → pack_submission → /saisresult/submission.zip
```

**可核验日志**：各阶段以 `[agent] phase=...` 写入运行日志，包含训练耗时、推理来源（inference / sample / baseline）、挂载路径探测结果。

---

## 三、模型结构与建模思路

### 3.1 KS 方程（problem1）

| 项 | 说明 |
|----|------|
| 模型 | **FNO1d**（Fourier Neural Operator，一维） |
| 训练数据 | `/saisdata/49/problem1/data/KS_train.hdf5`（及 val） |
| 测试 | A：`KS_test_A.hdf5`；B：`/saisdata/66/KS_test_B.hdf5` |
| 推理 | 自回归多步 rollout，float32 FFT |
| 预设 | `SHENJING_KS_PRESET=ks-q1`，`SHENJING_KS_EPOCHS=28` |

**方法适用域（通用经验，非本题泄露）**：

- 周期边界、中等非线性 KS：FNO 在中短时域较稳；
- 长时 rollout 误差累积明显时，应缩短 window 或加强 IC 对齐；
- 训练过重会挤占 6h 预算，导致 rollout 步数不足 — 宜在 preset 与时间预算间权衡。

### 3.2 Cylinder 绕流（problem2）

| 项 | 说明 |
|----|------|
| 模型 | **FNO**（二维场），权重由平台挂载 |
| 测试 | A：`cylinder_test_A.hdf5`；B：`cylinder_test_B.hdf5` |
| 路径 | `/saisdata/49/problem2/models/`、`inference/` |

cylinder 侧以 **挂载权重推理** 为主，避免在镜像内打包大体积 checkpoint。

---

## 四、数据处理流程

1. **不打包数据集**：训练/测试 HDF5 均由评测机挂载至 `/saisdata`；
2. **路径解析**：`first_existing` 兼容 `/saisdata/49/`、`/saisdata/48/`、`/saisdata/66/` 等多挂载形态；
3. **IC 一致性**：输出 tensor 前 20 步与测试输入对齐，容差 **5e-3**；
4. **兜底策略**（保证四文件存在，避免整题 0 分）：sample 复制、baseline 外推 — 日志中明确标注 `source=`。

---

## 五、环境依赖

| 组件 | 版本/说明 |
|------|-----------|
| 基础镜像 | `pytorch/pytorch:2.1.2-cuda12.1-cudnn8-runtime` |
| Python 包 | h5py, tqdm, matplotlib |
| GPU | V100 16G（评测限时 **6h**） |
| 入口 | `FUSAI_TRACK=shenjingsuanzi` |

代码位置：

- 运行：`/app/submit/tracks/shenjingsuanzi_agent/`
- 审核副本：`/app/agent_code/shenjingsuanzi_agent/`

---

## 六、复现步骤

```bash
# 评测环境
export FUSAI_TRACK=shenjingsuanzi
export SAISDATA=/saisdata
export SAISRESULT=/saisresult
sh /app/run.sh

# 本地（需挂载数据）
python3 /app/submit/main.py --track shenjingsuanzi \
  --saisdata /path/to/mount --saisresult /tmp/out --work-dir /app
```

验证：`submission.zip` 内含四个 HDF5；可用 `VALIDATION/check_submission.py --track shenjingsuanzi` 检查文件名。

---

## 七、外部服务与 API Key

本赛道 **不依赖 LLM API** 完成核心推理；若扩展文献检索 Skill，可通过环境变量配置（可选）：

| 变量 | 说明 |
|------|------|
| `SHENJING_LLM_API_KEY` | 可选，文献/假设辅助 |
| `SHENJING_LLM_BASE_URL` | OpenAI 兼容接口 |

---

## 八、镜像合规声明

**允许**：Agent 代码、PDE 知识库说明、运行时训练逻辑（Agent 内嵌）。  
**禁止**：打包训练集/测试集、预计算预测 HDF5、针对性本题超参文档。

---

## 九、创新点与后续优化

1. **A+B 双榜统一 pipeline**：单次运行产出四文件，独立计分互不影响；
2. **KS 训练状态跨榜复用**：B 榜在 A 榜训练状态上继续推理，节省预算；
3. **待优化**：KS 长时 rollout 与 6h 训练预算的平衡（参考 pdeburgers 基线 ~57.69）。

---

## 十、附件与代码索引

| 路径 | 内容 |
|------|------|
| `submit/tracks/shenjingsuanzi_agent/pipeline.py` | 主 Agent 编排 |
| `submit/tracks/shenjingsuanzi_agent/ks.py` | KS FNO 训练/推理 |
| `submit/tracks/shenjingsuanzi_agent/cylinder.py` | cylinder 推理 |
| `TASKS/shenjingsuanzi/SUBMISSION_SPEC.md` | 提交规范 |
