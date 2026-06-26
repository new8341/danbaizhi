# 蛋白质构象系综生成项目：启动指南与 Prompt 套件

本项目目标：用“AI 结构预测 + 分子模拟 + 动力学建模”生成并分析**蛋白质构象系综**，而不是只给出单一静态结构。

## 限定规则

document中文件为原始设定，运行程序与修改代码均不能改变；若有可能存在错误，可以经过我同意后进行改变；
实时代码位置保存在根目录下保持不变；

### 竞赛迭代与归档（与 §1.3 / §1.5 / Prompt 13 一致）

- **小步优化**：每次尽量只改一类因素；在 **`readme.md` §1.5** 追加一行优化记录；若有新想法，写入 §1.3 对应条目的 **「优化灵感」**。
- **何时必须跑「整包提交 + 评测」并归档 `daima/YYYYMMDDHHMM`**：当本轮改动**可能显著改变** `output.zip` 内构象几何、模板候选集合、或线上排行榜分数时，应用 **`generate_submission.py`（或等效打包流程）启动时刻**的本地时间作为目录名（12 位数字 **`YYYYMMDDHHMM`**，例如 `daima/202604302253`）；跑完后执行 **`scripts/archive_run.py --timestamp 上述同一时刻`**，保存当次涉及的 **相关代码** 与 **参赛结果数据**（含 `output.zip`、`local_eval.json`、`strategy_report.json`、`agent.log` 等，脚本默认会复制 `scripts/`、`configs/`、`document/`、**`tests/`**（若存在）、`data/public`、`results/submission` 等）。**补档**：对已存在的 **`daima/YYYYMMDDHHMM`** 可用 **`--supplement daima/...`** 合并 **`--extra-path`**，并可选 **`--refresh-submission`** / **`--refresh-timeline-zip`** 与当前工作区同步提交产物（详见脚本 `--help`）。
- **可不新建 `daima` 全量快照的情况**：纯文档、仅本地评测脚本增强、或代码/配置变更在**当前数据**下可证明与基线 **`output.zip` 字节级或几何级等价**（例如无序列条件候选时合并脚本默认参数不变）——仍须在 §1.5 说明「为何未归档」。
- **无 `results/openmm` 时**：若仅需归档提交产物，可将 `archive_run.py` 的 **`--run-dir`** 指向已有目录（例如 **`results/submission`**），只要该路径存在即可（与默认 `results/openmm` 二选一，满足「必须存在」校验）。
- **`daima/guidang`（当前最高分快照）**：与线上一致的最佳提交整包镜像，默认来自 **`daima/202605241146`**（**0.717129**，2026-05-24 11:54:09）。刷新命令：

```powershell
.\scripts\refresh_guidang.ps1 -SyncWorkspaceSubmission
```

线上刷新分数后：先归档新 `daima/YYYYMMDDHHMM`，再执行 `refresh_guidang.ps1 -SourceArchive daima\新目录 -OnlineScore <分>`。

---

## 1) 合规判断与下一阶段提分路线（先读）

本节基于 `document/rull.md` 的初赛规则与当前提交结果，判断后续优化方向是否合规，并给出按性价比排序的实施路径。核心红线：**不得使用赛题私有 GT 结构、GT ensemble 或原始 MD 轨迹**；可以使用公开数据库、公开预训练模型、公开工具和基于题目序列的预测结果。

### 1.1 当前方向是否合规

| 方向 | 合规性 | 原因与边界 |
| --- | --- | --- |
| **RCSB/PDB 公开模板 + `template_align` / `template_cif`** | 合规 | `document/rull.md` 允许使用 RCSB PDB 等公开数据库；不得手动导入本次赛题私有 GT 或轨迹。 |
| **ColabFold / AlphaFold / ESMFold / Chai / Boltz 基于题目序列预测结构** | 合规 | FAQ 明确允许 AlphaFold、ESMFold、Chai-1 等作为起点；必须只以赛题序列和公开模型/公开 MSA 为输入。 |
| **BioEmu / ConforMix 类构象采样模型** | 原则合规 | 若工具公开可用、输入仅为序列或公开先验，则符合“公开预训练模型/通用数据”精神；不得用赛题 GT 作 conditioning、筛选标签或重加权目标。 |
| **短程 OpenMM relaxation / energy minimization** | 合规 | 物理力场属于公开通用工具；用于修复 clash、几何和侧链合理性，不能用赛题 GT 作为约束。 |
| **根据线上分数做 A/B 选择** | 合规但需留痕 | 只用排行榜反馈选择方案通常可接受，但必须在 `agent.log` 与 `daima/YYYYMMDDHHMM` 归档中记录自动化迭代、配置与结果，避免“手工炼丹”不可审计。 |
| **直接使用或反推出本次赛题 GT / 原始 MD 轨迹** | 不合规 | 规则明确禁止使用本次赛题原始 MD 轨迹、晶体结构或 NMR ensemble 作为输入。 |

### 1.2 当前结果的主要瓶颈

当前锁版提交（如 `configs/submission_sources.lock_ab_202605051709.json`）已经解决了格式、长度、基础物理自检与 `agent.log` 合规问题。后续涨分瓶颈主要不在 mmCIF 打包，而在比赛评分的两块：

- **Base Score（50%）**：预测构象的 **CA-RMSD** 是否靠近未知 GT 系综。仅靠同源模板与几何扰动，可能离真实溶液构象分布仍有偏差。
- **Ensemble Quality（50%）**：多样性、PCA 覆盖、Boltzmann consistency、clash / Ramachandran 等。过散会伤 precision，过集中会伤 coverage 与 PCA 覆盖。

**线上 plateau 观察（2026-05-07～08）**：排行榜在 **0.700651** 与 **0.700629** 附近小幅波动；其中 **2026-05-07 22:01:17** 与 **2026-05-08 13:36:49** 两次均为 **0.700651**，而工程侧将 **`hybrid_sidechain_record_passes` 调至 4** 并未改变该分数，说明在**当前候选与模板池**下，继续微调 hybrid 侧链轮数**不是**线上主杠杆；应优先 §1.3 第 1 条（序列条件多工具候选）。

### 1.3 推荐提分路径（按性价比排序）

#### 当前竞赛基线（线上确认，2026-05-21 起）

- **排行榜最高分**：**0.717129**（**2026-05-24 11:54:09**，P1+P2+P3 完整 MSA ColabFold 先验，pLDDT≥50）；整包 **`daima/202605241146`**，镜像 **`daima/guidang`**；配置 **`configs/submission_sources.best.json`**（同 `sequence_prior`）。
- **上一档**：**0.704636**（`daima/202605212031`，仅 P2 MSA）；**历史 plateau**：**0.700651**（`daima/202605081315`）；**勿回退** preview **0.537492**（`daima/202605192200`）。
- **工程对齐**：三题主模板均为 **`predictions_msa/`** 高 pLDDT PDB；P1/P3 仍 **`template_align` + hybrid**（`hybrid_sidechain_record_passes=4`）；P2 **`template_cif`** 全原子扰动。

**进行中候选（本地）**：ColabFold **`--num-models 3`** 补跑（`scripts/run_colabfold_extra_models.ps1`）→ 多 rank PDB 并入候选池 → **`auto_finish_extra_models_pipeline.ps1`** 归档 A/B。

后续优化相对 **0.717129 / guidang** 小步迭代；见 `document/rull.md`：**Base Score（50%）** 靠高质量序列折叠与**多样构象覆盖**，**Ensemble Quality（50%）** 需兼顾 precision（勿盲目加低质构象）。

**文献对齐的最新数据处理思路（2024–2026，合规前提下）**：下列工作支持“用序列与公开 MSA/模型生成多构象分布”，与赛题 Base Score + Ensemble Quality 一致；按**预期提分 / 实现难度**排序已并入下表。

| 方向 | 机制（为何可能涨分） | 实现难度 | 公开线索 |
| --- | --- | --- | --- |
| 多工具序列条件候选池 + 现有 `diversity_filter` | 候选贴近真实序列，改善 CA-RMSD 系综对齐；筛选控 precision/coverage | **低–中**（本仓库已有合并脚本） | §1.4、`build_sequence_prior_sources.py` |
| ColabFold / AF2 **MSA 子采样或列掩码**（多样 seed） | 削弱单一共进化盆地，显式采样替代构象，文献报告系综/NMR 对齐提升 | **中**（调 batch 与 MSA 深度/随机性） | [Nat Commun 2024：subsampled AF2 系综](https://www.nature.com/articles/s41467-024-46715-9)、[Commun Biol 2025：AFsample2](https://www.nature.com/articles/s42003-025-07791-9) |
| **序列净化 / 富集共进化信号**（AF-ClaSeq 类） | 多态采样依赖“序列纯度”而非仅 MSA 深度，利于多稳态蛋白 | **中–高**（管线独立） | [arXiv:2503.00165](https://arxiv.org/abs/2503.00165) |
| **二级结构或中间表示引导**（ConforFold 类） | 超越纯 MSA 扰动，对双稳态恢复率更高 | **高**（新模型/新流程） | [PMC ConforFold](https://pmc.ncbi.nlm.nih.gov/articles/PMC13064411/) |
| **Boltz-2 + 构象采样**（pair 表示缩放 / confidence 筛选） | 在扩散式架构上系统探索潜空间，获多样低置信度备选 | **中–高**（依赖 GPU 与权重） | [Boltz-2 bioRxiv](https://www.biorxiv.org/content/10.1101/2025.06.14.659707)、[Boltz-sample steering（bioRxiv 2026-01）](https://www.biorxiv.org/content/10.64898/2026.01.23.701250v1.full-text) |
| **流匹配 / SE(3) 系综采样**（如 BBFlow 类） | 不依赖 MSA 亦可从 backbone 条件采样 Boltzmann 式系综，可作**额外候选 .cif** 来源 | **高**（独立模型与推理栈） | [arXiv:2503.05738](https://arxiv.org/abs/2503.05738) |
| **条件扩散 + 模态/局域几何对齐**（Mac-Diff 类） | 显式对齐序列条件与残基对几何，多亚稳态与别构蛋白的多样系综 | **高** | [Nature Machine Intelligence 2026](https://link.springer.com/article/10.1038/s42256-026-01198-9) |
| **推理期潜变量优化**（相对后验扰动） | 在生成过程中优化潜表示，更贴近实验系综、减少热力学不合理样本 | **中–高** | [arXiv:2602.24007](https://arxiv.org/abs/2602.24007) |
| **物理反馈对齐生成模型**（EBA 类） | 用能量差等物理信号校准多态占比，改善与 MD 系综基准的一致性 | **高** | [ICML 2025 proceedings](https://proceedings.mlr.press/v267/lu25b.html) |
| 短程 **OpenMM minimization / NVT** | 降 clash、改善 Ramachandran，抬 Ensemble Quality 物理子项 | **中**（需控步长避免跑离模板盆地） | §1.3 第 2 条 |

1. **高优先级：扩充序列条件候选池，再用现有筛选器选构象。**  
   使用 ColabFold / AlphaFold / ESMFold / Chai / Boltz 等公开工具对 `document/1.json`、`2.json`、`3.json` 的序列做多 seed、多模型预测；将输出加入 `template_cifs` 候选池，再用当前 `diversity_filter` 控制 precision / coverage 平衡。原因：候选本身更贴近目标序列，比继续微调同源模板阈值更可能提高 Base Score。
   - **优化灵感**：不要把候选池绑定到单一工具目录；可同时扫描 `results/colabfold`、`results/boltz`、`results/chai` 等多来源，形成“多工具候选池 + 长度校验 + 统一筛选”的可审计流程。
   - **优化灵感**：对 ColabFold/AF2 批跑显式记录 **随机种子、MSA 深度、是否子采样列**；与 `daima/YYYYMMDDHHMM` 一一对应，便于 A/B 与合规审计。
   - **优化灵感**：同一题多目录合并时，可用 `build_sequence_prior_sources.py --candidate-sort mtime_desc` 让**较新预测**排在候选列表前部（默认仍为路径字典序，不改变现有行为）。
   - **优化灵感**：扩散/流匹配工具若仅输出**公开模型、仅序列条件**的多个 `.cif`，可像 ColabFold 一样放入 `results/<tool>/problem_{id}/`，由 `build_sequence_prior_sources.py` 合入；优先在本地用 `eval_submission_local.py` 与 `heavy_atom_clash_proxy` 做预筛再进主 `diversity_filter`，避免为多样性牺牲物理项。
   - **优化灵感**：多工具合并后若单题预测文件极多，先用 **`--max-prior-per-problem N`**（配合 `--candidate-sort mtime_desc`）控制进入 `template_cifs` 的序列条件条数，再在 `generate_submission` 层用 `diversity_filter` 选最终构象，通常比「无限制堆模板」更稳。

2. **中优先级：对最终候选做短程 relaxation。**  
   对选出的全原子 mmCIF 做 energy minimization 或很短 NVT relaxation，目标是降低 clash 与不合理二面角，提升 Ensemble Quality 中的物理合理性子项。要求：不能用 GT 约束，只用公开力场。
   - **优化灵感**：先用 `eval_submission_local.py` 的 `heavy_atom_clash_proxy` 找出 P1/P3 中全原子冲突更高的问题构象，再只对这些构象做局部 relaxation 或替换模板，避免无差别 MD 带来不必要扰动。
   - **优化灵感**：在 hybrid 全原子写出流程中，可在 JSON 里调节 **`hybrid_sidechain_record_passes`**（二次网格侧链避碰的最大轮数，默认 3）；在仍无序列条件候选时，这是低成本微调物理子项的旋钮，改后需全量重打包并归档 `daima/YYYYMMDDHHMM` 做 A/B。

3. **中优先级：保留锁版并进行 A/B 线上验证。**  
   继续保留 `configs/submission_sources.lock_ab_202605051709.json` 作为可回滚基线（文件名沿用历史 A/B 标签；内容在确认 hybrid / 侧链管线更优后可与 `public.json` 对齐，见 §1.5）。每次新策略都独立生成 `output.zip` 并归档到 `daima/YYYYMMDDHHMM`；只有线上分数和本地自检同时更优时才把锁版 JSON 与 public 对齐。

4. **低优先级：继续单独调 `diversity_filter` 阈值。**  
   线上已有轻微提升说明筛选方向有效，但当前本地试验显示阈值过强会让 P1 过集中，收益已进入边际递减。后续应围绕更好的候选池调参，而不是仅在原有候选上反复扫阈值。

### 1.4 下一步可执行命令模板

当前稳态锁版复现：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.lock_ab_202605051709.json --with-local-eval --note "lock baseline"
python scripts/archive_run.py --note "lock baseline"
```

如果本机装好 ColabFold 或设置了 `COLABFOLD_BATCH`，先生成序列条件候选：

```bash
python scripts/run_colabfold_optional.py
```

**仅 WSL 内安装了 LocalColabFold（pixi）时（Windows 上无原生 `colabfold_batch`）**：在仓库根目录的 PowerShell 中可先设环境变量再跑（脚本会把 FASTA 与输出目录从 Windows 路径转为 WSL 路径）：

```powershell
$env:COLABFOLD_WSL = "1"
python scripts/run_colabfold_optional.py --dry-run
```

或直接指定包装器（等价）：`$env:COLABFOLD_BATCH = "$PWD\scripts\colabfold_batch_wsl.cmd"`。可选：`COLABFOLD_WSL_DISTRO`（默认 `Ubuntu-22.04`）、`COLABFOLD_WSL_BIN`（覆盖默认的 `.../localcolabfold-main/.pixi/envs/default/bin/colabfold_batch`）。WSL 内需已执行 `pixi install` 与 `pixi run setup`，且 `PATH` 能访问 `colabfold_batch`（包装脚本会预置 `$HOME/.pixi/bin`）。若 WSL 内 **GPU 过旧**、JAX/CUDA 易挂起，可设 **`$env:COLABFOLD_WSL_CPU = "1"`**（在 WSL 子进程内 **`JAX_PLATFORMS=cpu`**）。**权重缓存（约 3.5GB）**：设 **`$env:COLABFOLD_WSL_XDG_CACHE = "$PWD\data\colabfold_xdg_cache"`**（仓库下自建目录即可），使下载落在 **Windows 盘挂载路径**，避免占满 WSL 根分区、便于断点续传与复用。也可 **`cd` 到仓库根目录后执行** **`. .\scripts\colabfold_wsl_env.ps1`**（点源脚本）一次设好 **`COLABFOLD_WSL` / `COLABFOLD_WSL_CPU` / `COLABFOLD_WSL_XDG_CACHE`** 并打印当前缓存目录占用。

**先跑通管线（单序列、无 MSA 服务器）**：`--fast-preview` 等价于 **`--num-models 1`**、**`--num-recycle 1`** 与 **`--msa-mode single_sequence`**（质量低于完整 MSA，但易产出 `.pdb`/`.cif` 以验证 `build_sequence_prior_sources`）：

```powershell
$env:COLABFOLD_WSL = "1"
$env:COLABFOLD_WSL_CPU = "1"
python scripts/run_colabfold_optional.py --fast-preview --dry-run
```

**只跑某一题（链更短，便于先打通）**：例如题 2 序列较短，可先 **`--only-problem 2`**（可重复该参数跑多题）：

```powershell
$env:COLABFOLD_WSL = "1"
$env:COLABFOLD_WSL_CPU = "1"
$env:COLABFOLD_WSL_XDG_CACHE = "$PWD\data\colabfold_xdg_cache"
python scripts/run_colabfold_optional.py --only-problem 2 --fast-preview
```

若本地 ColabFold 支持额外开关（如 MSA 模式、amber 等），可对 `colabfold_batch` **追加参数**（每参数重复一次 `--batch-arg`）：

```bash
python scripts/run_colabfold_optional.py --batch-arg --amber
```

随后把 `results/colabfold/problem_{id}/...`（及 Boltz/Chai 根目录）中的预测合入配置并打包（**推荐**：新预测在前 + 每题最多 24 个序列条件文件；**无预测时**与 `public`/`lock` 模板列表一致，生成结果即基线）：

```bash
python scripts/build_sequence_prior_sources.py --base-config configs/submission_sources.public.json --candidate-root results/colabfold --extra-candidate-root results/boltz --extra-candidate-root results/chai --out-config configs/submission_sources.sequence_prior.json --prefer-sequence-prior --candidate-sort mtime_desc --max-prior-per-problem 24
python scripts/generate_submission.py --sources-config configs/submission_sources.sequence_prior.json --with-local-eval --note "sequence-prior candidate pool"
```

**一键（PowerShell，含可选归档）**：

```powershell
.\scripts\run_sequence_prior_pipeline.ps1 -Archive -Note "sequence prior after colabfold"
```

**ColabFold 长跑完成后自动合并（含 pLDDT 门槛，默认不冲榜低分预览结构）**：

```powershell
.\scripts\watch_colabfold_and_archive.ps1 -ProblemId 3 -Archive
# 日志：results/colabfold/problem_{id}/watch_archive.log
# 仅验证管线、不归档：去掉 -Archive
```

**P3 完成后自动合并 P2+P3 MSA 并归档**（后台一条链即可）：

```powershell
.\scripts\auto_finish_msa_pipeline.ps1
# 日志：results/colabfold/auto_finish_msa.log
# 出 P3 PDB 后生成新 daima/YYYYMMDDHHMM（含 P2+P3 predictions_msa，pLDDT≥50）
```

**P1 MSA 完成后自动合并 P1+P2+P3 并归档**：

```powershell
.\scripts\auto_finish_p1_msa_pipeline.ps1
# 日志：results/colabfold/auto_finish_p1_msa.log
```

**在全新目录 `predictions_msa_3m/` 跑 3 个 AF2 模型**（从 `predictions_msa/` 复制 MSA，避免 ColabFold「already done」跳过）：

```powershell
. .\scripts\colabfold_wsl_env.ps1
.\scripts\run_colabfold_extra_models.ps1          # 输出 predictions_msa_3m/，P3→P2→P1
Start-Process powershell -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','.\scripts\watch_extra_models_and_notify.ps1' -WindowStyle Hidden
# 通知文件（完成/中断/续跑）：results/colabfold/USER_NOTIFY.txt
# 日志：results/colabfold/watch_extra_models.log、extra_models.log
# build_sequence_prior 会 rglob 扫描 problem_{id}/ 下全部 .pdb（含 msa 与 msa_3m）
```

若本次生成**可能显著改变**提交几何或线上分，再在 **`generate_submission` 启动时刻**取 `YYYYMMDDHHMM` 并执行：

```bash
python scripts/archive_run.py --run-dir results/submission --timestamp YYYYMMDDHHMM --note "sequence-prior candidate pool"
```

仅当需要更少/更多序列条件槽位时，可改 `--max-prior-per-problem`（`0` 表示不限制）。截断信息写入对应题目的 **`sequence_prior_cap`** 与 `results/sequence_prior/summary.json` 的 `problems[pid].prior_cap`。

默认会用 `mdtraj` 校验候选结构的 **CA 数是否等于题目序列长度**；不合格候选会写入 `sequence_prior_rejected`，不会进入 `template_cifs`。默认还会用 ColabFold 旁路 **`_scores_*.json`**（或 PDB CA B-factor）过滤 **mean pLDDT &lt; 50**（`--min-mean-plddt`，`0` 关闭）；**`fast-preview`（pLDDT≈29）会被拒**，避免再次冲榜 **`0.537492`** 类失败。脚本同时写出 `results/sequence_prior/summary.json`，记录扫描目录、校验参数、每题接收/拒绝数量，便于归档和 `agent.log` 审计。如确需容忍轻微缺口，可加 `--max-length-delta N`；如只想生成清单不校验，可加 `--no-validate-candidates`。

归档时若不存在 `results/openmm`，可将 **`--run-dir`** 设为已有目录（常用 **`results/submission`**），以便通过 `archive_run.py` 的存在性校验：

```bash
python scripts/archive_run.py --run-dir results/submission --timestamp YYYYMMDDHHMM --note "submission-only snapshot after generate_submission"
```

### 1.5 优化记录（逐步推进）

| 时间 | 改动 | 结论 | 后续动作 |
| --- | --- | --- | --- |
| 2026-05-06 12:40 | 使用锁版配置 `configs/submission_sources.lock_ab_202605051709.json` 生成并归档，路径 `daima/202605061240`。 | 稳态基线可复现，适合作为线上 A/B 与回滚基准。 | 当时约定日常改 `public`；后续 hybrid 管线确认后锁版已与 public 对齐（见 2026-05-08 行）。 |
| 2026-05-06 12:44 | 对比比赛评分规则、当前本地指标与最新公开方法，判断下一阶段主线。 | 单纯阈值调参收益递减；更优方向是扩充序列条件候选池。 | 优先接入 ColabFold / AlphaFold / ESMFold / Chai / Boltz 输出。 |
| 2026-05-06 12:51 | 尝试 P1 离群裁剪筛选（`trim_outlier_quantile` / `max_mean_distance_A`）。 | 本地 P1 pairwise mean 被压到约 1.14 Å，过于集中，coverage 风险上升。 | 保留代码能力，但不作为默认提交配置。 |
| 2026-05-06 13:05 | 将实验性离群裁剪配置另存为 `configs/submission_sources.experimental_outlier_trim.json`，并把 `configs/submission_sources.public.json` 恢复到锁版稳态。 | 默认生成路径回到线上略有提升且更稳的候选；实验配置可追溯。 | 下一步只在“更好候选池”基础上再启用筛选。 |
| 2026-05-06 13:07 | 新增 `scripts/build_sequence_prior_sources.py`，自动扫描 `results/colabfold/problem_{id}/` 下的 `.cif` / `.mmcif` / `.pdb`，生成 `configs/submission_sources.sequence_prior.json`。 | 当前本机尚无 ColabFold 输出，候选数为 0；脚本与配置生成链路已跑通。 | 安装/运行 ColabFold 后无需手工改 JSON，直接重跑该脚本即可合入序列条件候选。 |
| 2026-05-06 13:12 | 为 `scripts/build_sequence_prior_sources.py` 增加候选 CA 长度校验与 `sequence_prior_rejected` 记录。 | 防止错误链、截断模型或非目标结构进入 `template_cifs`；当前无本地候选，提交包不会变化，因此无需本轮归档。 | 后续若 ColabFold 输出存在，先看 `sequence_prior_rejected` 再决定是否放宽 `--max-length-delta`。 |
| 2026-05-06 13:15 | 为 `scripts/build_sequence_prior_sources.py` 增加 `results/sequence_prior/summary.json` 审计报告。 | 本轮仅生成候选池审计信息，三题 accepted/rejected 均为 0，不改变提交包与跑分。 | 后续有候选后，该报告随归档保存，用于解释候选接入是否合规、是否被长度过滤。 |
| 2026-05-06 13:17 | 为 `scripts/build_sequence_prior_sources.py` 增加 `--extra-candidate-root`，支持同时扫描 ColabFold / Boltz / Chai 等多个候选来源。 | 当前多来源扫描链路已跑通，三题候选仍为 0，不改变提交包与跑分。 | 未来不同工具输出放入对应 `results/{tool}/problem_{id}/` 后，可统一合入并做长度校验。 |
| 2026-05-06 13:22 | 在 `scripts/generate_submission.py` 中新增 hybrid 构象短相邻 CA 修复，并在 `configs/submission_sources.public.json` 对 P1/P3 启用 `repair_hybrid_short_ca`。 | 本地评测显示 P1 `frac_short_bonds_mean` 从非零降为 0，P1 clash proxy 小幅下降，pairwise 分布基本不变；已生成并归档 `daima/202605061322`。 | 可作为候选提交版本；若线上确认提升，再同步更新 lock 配置。 |
| 2026-05-06 19:51 | 为 `scripts/eval_submission_local.py` 增加 `heavy_atom_clash_proxy`（网格近邻、排除同/邻残基）。 | 本轮仅增强评测能力，不改变提交包；当前结果显示 P1 heavy-atom clash proxy 高于 P2/P3，是下一步物理项优化重点。 | 后续优先针对 P1 高 clash 构象做局部 relaxation 或替换为更合理的序列条件候选。 |
| 2026-05-07 12:58 | 在 `scripts/generate_submission.py` 中新增网格化 hybrid 侧链避碰，并在 `configs/submission_sources.public.json` 对 P1/P3 启用 `relieve_hybrid_sidechain_clashes`。 | 初版逐原子全表扫描过慢，已改为网格近邻；本地评测显示 P1 heavy-atom clash proxy 从约 0.00578 降至 0.00383，P3 从约 0.00141 降至 0.00130，CA 分布基本不变；已归档 `daima/202605071258`。 | 若线上确认物理项提升，可同步更新 lock 配置；若 precision 下降，则关闭该开关回滚。 |
| 2026-05-07 13:09 | 在 `scripts/generate_submission.py` 中增加二次 sidechain clash relief，对完整 hybrid atom record 再做一轮网格近邻避碰。 | P1 heavy-atom clash proxy 继续降至约 0.00344，P3 降至约 0.00093；CA pairwise 与长度指标保持稳定；已归档 `daima/202605071309`。 | 可作为下一版候选提交；若线上分数提升，更新 lock；若 precision 或解析回退，关闭 `relieve_hybrid_sidechain_clashes` 回滚。 |
| 2026-05-08 12:54 | 将 `configs/submission_sources.lock_ab_202605051709.json` 与当前 `configs/submission_sources.public.json` 对齐：P1/P3 启用 `repair_hybrid_short_ca`、`relieve_hybrid_sidechain_clashes` 及阈值字段；P1 仍开 diversity、P3 仍关。 | 锁版复现命令与线上候选管线一致；几何与 public 提交等价，可能改变与旧锁版（无 hybrid 修复）的 diff；已全量生成评测并归档 `daima/202605081254`。 | 历史纯 A/B 锁体仍以归档 `daima/202605051709` 与 `daima/202605061240` 追溯；日常实验继续改 `public.json`。 |
| 2026-05-08 | 检索 2024–2026 多构象/系综公开方法（MSA 子采样、AFsample2、AF-ClaSeq、ConforFold、Boltz-2/Boltz-sample）；在 §1.3 增加文献表与基线说明；新增 §1.6 与 §5「Prompt 13」竞赛提分 Prompt。 | 文档与规划对齐前沿；不改变默认提交。 | 有本地序列条件候选后，用 Prompt 13 驱动一轮可审计迭代；若合并策略或模型输出改变几何，再全量 `generate_submission` 并归档 `daima/YYYYMMDDHHMM`。 |
| 2026-05-08 | `scripts/build_sequence_prior_sources.py` 增加 `--candidate-sort mtime_desc`（默认 `path`，与旧版一致）。 | 仅在存在序列条件文件时影响候选顺序；当前仓库无候选时 `output.zip` 与锁版生成结果一致，故未新增 `daima` 全量归档。 | 接入 ColabFold/Boltz 输出后按需尝试 `mtime_desc` 并对比 `local_eval.json`。 |
| 2026-05-08 13:07 | 二次检索 2025–2026：流匹配/BBFlow、Mac-Diff（Nat Mach Intell）、推理期系综优化（arXiv:2602.24007）、物理对齐生成 EBA（ICML 2025）；扩充 §1.3 文献表与优化灵感；在「限定规则」与 §1.4 明确「小步记录 vs 必须跑模型+`daima/YYYYMMDDHHMM`」触发条件及 `--run-dir results/submission` 归档方式；§1.6 任务 5 与 Prompt 13 对齐该流程。 | 本轮为规划与文档对齐，不改变默认配置与 `output.zip`；故未执行 `generate_submission`、未新建 `daima`。 | 下一小步优先：按 §1.4 接入序列条件候选；若合并/模型输出改变几何，再启动整包生成并以启动时刻归档。 |
| 2026-05-08 13:15 | 按 §1.3 中优先级物理子项：`scripts/generate_submission.py` 将 hybrid 二次侧链避碰轮数外置为 **`hybrid_sidechain_record_passes`**；`configs/submission_sources.public.json` 与 **`configs/submission_sources.lock_ab_202605051709.json`** 对 P1/P3 设为 **4**（默认 3）。 | 本地 P1 `heavy_atom_clash_proxy.frac_mean` 约 **0.00339**（此前约 0.00344），P3 仍约 **0.00093**；CA pairwise、`frac_short_bonds_mean` 不变；已整包生成评测并归档 **`daima/202605081315`**。 | 线上 A/B；若 precision 回退可将该字段改回 **3** 或关闭 `relieve_hybrid_sidechain_clashes`。 |
| 2026-05-08 13:36 | 用户反馈：线上 **0.700651**（2026-05-08 13:36:49）与 **0.700651**（2026-05-07 22:01:17）同分，相对 05-06/05-05 仅小幅 plateau；**`hybrid_sidechain_record_passes=4` 未改变排行榜**。 | 将 **0.700651 + 当前 lock/public + `daima/202605081315`** 定为**新基线**；确认侧链轮数微调主要影响本地 proxy，主杠杆在 **Base Score（序列条件候选）**。 | 已建 `results/colabfold`、`results/boltz`、`results/chai` 占位目录；`run_colabfold_optional.py` 增加 `--batch-arg` 便于 MSA/模型多样性实验；下一步跑通 ColabFold/Boltz 后走 §1.4 `build_sequence_prior_sources`。 |
| 2026-05-08 | 延续 §1.3 高优先级：`build_sequence_prior_sources.py` 增加 **`--max-prior-per-problem`**（默认 `0` 不限制；去重后截断并写入 **`sequence_prior_cap`** 与 `summary.json` 的 `prior_cap`）；新增 `tests/test_sequence_prior_cap.py`。 | 当前仍无序列条件文件，不改变 `output.zip` 与线上分；已重生成 `configs/submission_sources.sequence_prior.json` 与 `results/sequence_prior/summary.json`。 | ColabFold 产出较多时，建议 `--candidate-sort mtime_desc --max-prior-per-problem 24` 再跑 `generate_submission` 并归档 `daima/YYYYMMDDHHMM`。 |
| 2026-05-08 | 用户确认执行 §1.4 推荐链：`run_colabfold_optional`（本机无 `colabfold_batch` → SKIP）→ `build_sequence_prior_sources`（`--prefer-sequence-prior --candidate-sort mtime_desc --max-prior-per-problem 24`）→ `generate_submission.py --sources-config configs/submission_sources.sequence_prior.json --with-local-eval`。 | 三题 `sequence_prior_candidates=0`，`local_eval` 与 **0.700651 基线**（`hybrid_sidechain_record_passes=4`）一致（如 P1 heavy-atom clash proxy frac_mean ≈ 0.00339）；**未新建 `daima`**（提交几何相对 `daima/202605081315` 等价）。 | 安装 LocalColabFold 或设置 `COLABFOLD_BATCH` 后重跑链首步；一旦有有效 `.cif`/`.pdb` 合入，再整包归档新 `daima/YYYYMMDDHHMM`。 |
| 2026-05-08 22:12 | 用户提供 `localcolabfold-main.zip`，已解压并按官方路径尝试安装：检查 `wsl --list --online`，执行 `wsl --install -d Ubuntu-22.04`。 | `localcolabfold` 该版本要求 WSL2 + Linux/pixi；当前机器在 WSL 安装阶段报 `Wsl/InstallDistro/WININET_E_CANNOT_CONNECT`，导致无法完成安装与生成 `colabfold_batch`。 | 先恢复网络/代理使 `wsl --install` 可联网，再在 WSL 内执行 `pixi install && pixi run setup`；完成后继续 §1.4 链路并在有候选时整包归档。 |
| 2026-05-08 22:23 | 用户确认已完成代理/DNS 调整后复测：`Resolve-DnsName aka.ms` 已解析到公网地址；再次执行 `wsl --install -d Ubuntu-22.04`。 | 仍失败，错误 **`HCS_E_HYPERV_NOT_INSTALLED`**：未启用 **虚拟机平台**（或 BIOS 未开硬件虚拟化），WSL2 无法创建 VM；`localcolabfold-main/pyproject.toml` 中 pixi 仅 **`linux-64` / `linux-aarch64` / `osx-arm64`**，无原生 Windows 目标。 | **管理员** PowerShell：`dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart` 与 `Microsoft-Windows-Subsystem-Linux`；控制面板「启用或关闭 Windows 功能」勾选同上；BIOS 开启 **Intel VT-x / AMD-V**；重启后执行 `wsl --set-default-version 2` 再 `wsl --install -d Ubuntu-22.04`；进入 WSL 后在挂载的 `.../localcolabfold-main` 目录运行 `pixi install && pixi run setup`，将 `.../.pixi/envs/default/bin/colabfold_batch` 设到 `COLABFOLD_BATCH` 或 PATH。 |
| 2026-05-09 | BIOS 开 VT-x 并重启后 WSL2 / Ubuntu-22.04 可用；仓库增加 **`scripts/colabfold_batch_wsl.py`**、**`colabfold_batch_wsl.cmd`**；**`run_colabfold_optional.py`** 在 Windows 上支持 **`COLABFOLD_WSL=1`** 自动选用包装器；§1.4 补充 WSL-only 用法；**`tests/test_colabfold_batch_wsl.py`**；WSL 内 **`pixi run setup`** 已跑通。 | 基础设施：ColabFold 仅在 WSL 时也可从 Windows 调用；**不改变**无候选时的 `output.zip`；无需新建 `daima`。 | 设 `COLABFOLD_WSL=1` 后跑 `run_colabfold_optional`（可先 `--dry-run`）；`pixi install` 超时则提高 **`UV_HTTP_TIMEOUT`** 重试。 |
| 2026-05-09 | **`colabfold_batch_wsl.py`**：调用 `wslpath` 前将盘符路径规范为 **`E:/...`**，避免 **`wsl.exe` 吞掉反斜杠** 导致 `wslpath: E:cursor...`；**`run_colabfold_optional.py`** 对 **`[CMD]` / `[DONE]`** 使用 **`flush=True`**；**`tests/test_colabfold_batch_wsl.py`** 增加路径规范化用例。 | 真跑预测可正常进入 WSL 内 ColabFold；终端里 TensorFlow/cuDNN「已注册」类警告多为良性。 | 产物看 **`results/colabfold/problem_*/predictions/`**；全三题耗时可很长（视 GPU/CPU 与 MSA）。 |
| 2026-05-10 01:02 | 助手执行：`build_sequence_prior_sources`（`mtime_desc`、`max-prior-per-problem 24`）→ **`generate_submission.py`**（`configs/submission_sources.sequence_prior.json`、`--with-local-eval`）→ **`archive_run.py`**（`--run-dir results/submission`、`--timestamp 202605100102`，`--extra-path` **`results/colabfold`** 与 **`results/sequence_prior`**）。 | 当时 **`results/colabfold`** 下尚无合格 **`.pdb`/`.cif`**（ColabFold WSL 长任务可能仍在跑），三题 **`sequence_prior_candidates=0`**；**`local_eval`** 与基线一致（如 P1 heavy-atom clash proxy frac_mean ≈ **0.00339**）；整包归档 **`daima/202605100102`**。 | ColabFold 产出 `.pdb`/`.cif` 后重跑链首步并再 **`generate_submission`**；若 **`output.zip`** 可能变样，再以新启动时刻归档 **`daima/YYYYMMDDHHMM`**。 |
| 2026-05-12 | **`archive_run.py`**：默认归档增加 **`tests/`**；新增 **`--supplement`**（向已有 **`daima/YYYYMMDDHHMM`** 合并 **`extra/`**、写入 **`supplement_log`**、保留原 **`created_at`**）、**`--refresh-submission`**、**`--refresh-timeline-zip`**；新增 **`tests/test_archive_supplement.py`**；对 **`daima/202605100102`** 补档 **tests**、**localcolabfold-main/pyproject.toml**、**results/boltz**、**results/chai** 并刷新 **`results/submission`** 与根目录 **`output.zip`**。 | 该次快照与当前工作区提交目录及多工具占位一致，便于审计 ColabFold/WSL 与序列先验管线；**未新建**其它 `daima` 目录。 | 既往归档缺项时优先 **`--supplement`**；新整包归档默认已含 **tests**。 |
| 2026-05-12 20:32 | 用户请求：以启动时刻 **`202605122032`** 执行 **`generate_submission.py`**（**`configs/submission_sources.public.json`**、`--with-local-eval`）→ **`archive_run.py`**（`--run-dir results/submission`、`--timestamp 202605122032`，`--extra-path`** **`results/colabfold`**、**`results/sequence_prior`**、**`results/boltz`**、**`results/chai`**、**`localcolabfold-main/pyproject.toml`**）。 | 新整包归档 **`daima/202605122032`**（含 **`tests/`**、**`output.zip`**、**`manifest.json`**）；`local_eval` 与 public 基线一致（如 P1 heavy-atom clash proxy frac_mean ≈ **0.00339**）。 | 若需锁版复现可改用 **`configs/submission_sources.lock_ab_202605051709.json`** 再生成并另取时刻归档。 |
| 2026-05-12 22:14 | 用户确认：以启动时刻 **`202605122214`** 执行 **`generate_submission.py`**（**`configs/submission_sources.lock_ab_202605051709.json`**，`--with-local-eval`）→ **`archive_run.py`**（同上一轮 **`extra-path`** 集合）。 | 与 **线上锁版 / public 对齐** 的整包归档 **`daima/202605122214`**；`output.zip` 约 **1.86 MB**，`local_eval` 与 public 基线一致。 | 日常实验仍改 **`public.json`**；提交前对齐锁版时用本流程。 |
| 2026-05-12 | **`run_colabfold_optional.py`**：文档补充 **`COLABFOLD_WSL_CPU`**；新增 **`--fast-preview`**（1 模型、1 recycle、**`single_sequence`** MSA）；**`tests/test_run_colabfold_optional_fast_preview.py`**；§1.4 增加 WSL 弱 GPU + 快速验证命令。 | 降低 ColabFold 在 WSL/旧卡上「长时间无输出」概率，便于尽快得到序列条件文件再走 **`build_sequence_prior_sources`**；**不改变**未跑 ColabFold 时的默认 **`output.zip`**。 | 有稳定 GPU/网络后去掉 **`--fast-preview`** 与 **`COLABFOLD_WSL_CPU`** 做正式 MSA 多模型；产出后按 §1.4 合并并视几何变化归档 **`daima/YYYYMMDDHHMM`**。 |
| 2026-05-13 12:35 | 用户「跑完归档」：`build_sequence_prior_sources`（`mtime_desc`、`max-prior-per-problem 24`）→ **`generate_submission.py`**（`configs/submission_sources.sequence_prior.json`，启动时刻 **`202605131235`**）→ **`archive_run.py`**（`--run-dir results/submission`、`--timestamp 202605131235`，`extra-path` 含 **colabfold / sequence_prior / boltz / chai / pyproject**）。 | 三题 **`sequence_prior_candidates=0`**（`results/colabfold` 仍无合格结构文件）；**`local_eval`** 与 public 基线一致；整包 **`daima/202605131235`**。 | ColabFold 产出 **`.pdb`/`.cif`** 后重跑本链；若 **`output.zip`** 可能变样，可再以新启动时刻归档。 |
| 2026-05-14 07:42 | 线上「基于基准优化」分数未动；主瓶颈仍为 **无序列条件文件**。在 **`configs/submission_sources.public.json`** 将 **P1** **`diversity_filter.candidate_multiplier`** **2→3**（`template_align` 候选池 **`min(10, 4×3)`**）；**`generate_submission.py`**（`public`）+ 本地评测；**`archive_run.py`** **`daima/202605140742`**。 | **P1** `pairwise_ca_rmsd_A.mean` 约 **19.37→25.21 Å**（系综更散），**`heavy_atom_clash_proxy.frac_mean`** 约 **0.00339→0.00385**（物理 proxy 略升）；P2/P3 不变；**锁版 JSON 未改**。 | 线上 A/B；若 precision 降或分不升，将 **multiplier 改回 2**；提分主杠杆仍是 **ColabFold/Boltz/Chai 序列候选**（`--fast-preview` + **`COLABFOLD_WSL_CPU`** 先跑通产出）。 |
| 2026-05-18 22:34 | 用户提交 **`daima/202605140742`** 对应 **`output.zip`**（P1 **`candidate_multiplier=3`**）：排行榜 **0.695038**（相对基线 **0.700651** 约 **−0.0056**）。 | **线上 A/B 否定**「仅加大 P1 diversity 候选池」路径；**`configs/submission_sources.public.json`** 已将 P1 **`candidate_multiplier` 改回 2**；日常提交仍以 **lock / `daima/202605081315`** 为准。 | 不再单独扫 P1 multiplier；优先 **序列条件候选**（ColabFold 权重下完后 **`build_sequence_prior_sources`**）或其它合规新候选来源。 |
| 2026-05-14 | **`run_colabfold_optional.py`**：新增 **`--only-problem N`**（可重复，默认仍跑 1–3）；§1.4 补充「先跑题 2」示例；**`tests/test_run_colabfold_optional_fast_preview.py`** 增加子集用例。 | 缩短首次出 **`.pdb`** 的等待（先 P2 再扩到 P1/P3）；不改变无 ColabFold 时的 **`output.zip`**。 | 本机：`COLABFOLD_WSL`+`COLABFOLD_WSL_CPU` + **`--only-problem 2 --fast-preview`**；有文件后 **`build_sequence_prior_sources`** → **`generate_submission(sequence_prior)`** 并视情况 **`daima/YYYYMMDDHHMM`**。 |
| 2026-05-14 | **`colabfold_batch_wsl.py`**：支持 **`COLABFOLD_WSL_XDG_CACHE`**（Windows 目录 → WSL **`XDG_CACHE_HOME`**），脚本会 **`mkdir`**；§1.4 与「先跑题 2」命令中补充 **`data\colabfold_xdg_cache`**；**`tests/test_colabfold_batch_wsl.py`** 增加 **`XDG_CACHE_HOME`** 断言。 | ColabFold 首次运行需下载 **~3.5GB** AlphaFold 权重；缓存在 **E: 挂载盘** 可减轻 **`/root/.cache`** 压力、利于断点续传；**不改变**未跑推理时的提交产物。 | 若当前下载极慢：设 **`COLABFOLD_WSL_XDG_CACHE`** 后**重新启动**一次批跑（已下在 `/root/.cache` 的进度不会自动迁移）。 |
| 2026-05-14 | 新增 **`scripts/colabfold_wsl_env.ps1`**（点源后设三项 **`COLABFOLD_*`** 并打印 **`data\colabfold_xdg_cache`** 占用）；§1.4 引用该脚本。 | 减少手敲路径错误；**不改变**提交与评测逻辑。 | 本机 ColabFold 下载完成后跑 **`build_sequence_prior_sources`** → **`generate_submission`**。 |
| 2026-05-18 22:53 | 按规划跑通序列先验整链：新增 **`scripts/run_sequence_prior_pipeline.ps1`**；在 **`results/colabfold`** 放入 interim **`.cif`**（P2 **`3Q43`** 通过长度校验；P1 两文件 **rejected**）；**`generate_submission(sequence_prior)`** + 归档 **`daima/202605182253`**。ColabFold 真预测仍卡在权重下载（WSL **`/root/.cache`** 续传）。 | **P2** `pairwise_ca_rmsd_A.mean` 约 **2.59→2.79 Å**；P1/P3 与 lock 基线一致；**`output.zip` 几何已变（主要来自 P2）**。 | **勿用 interim CIF 冲榜**；权重下完后用真 **ColabFold `.pdb`** 重跑 **`run_sequence_prior_pipeline.ps1 -Archive`** 再线上 A/B。 |
| 2026-05-19 13:45 | **方式 A 权重就绪**：停止慢速 `wget`，自 WSL **`/root/.cache/colabfold`**（已含 **`download_finished.txt`**）**`rsync`** 至 **`data/colabfold_xdg_cache`**（约 **3.5 GB**）；**`--only-problem 2 --fast-preview`** 产出 **`p2_unrelaxed_rank_001_...pdb`**；删除 interim **`p2_prior_3Q43.cif`** 后 **`run_sequence_prior_pipeline.ps1 -Archive`** → **`daima/202605191345`**。 | **P2** `sequence_prior_candidates=1`（真 AF2 PDB）；**P1** 仍 **rejected**（旧 homolog CIF 长度不符）；**P2** `pairwise_ca_rmsd_A.mean` 约 **21.52 Å**（`fast-preview` 质量有限）；**`output.zip` 已变**。 | 线上 A/B **`daima/202605191345`**；P1/P3 去 interim 后跑 ColabFold（去 **`--fast-preview`** 或增模型/recycle）；勿提交 **`daima/202605182253`** / **`202605140742`**。 |
| 2026-05-19 22:00 | **P1 ColabFold 完成**（`--only-problem 1 --fast-preview`，CPU 约 **8.3 h** / 1104 aa）：产出 **`p1_unrelaxed_rank_001_...pdb`**（pLDDT≈29）；删除 interim **`p1_prior_3Q22/3C46.cif`**；**`scripts/watch_p1_colabfold_and_archive.ps1`** 轮询后自动 **`run_sequence_prior_pipeline.ps1 -Archive`** → **`daima/202605192200`**。 | **P1+P2** 各 **1** 个序列先验（真 PDB）；**P1** `pairwise_ca_rmsd_A.mean` 约 **19.37→37.21 Å**，**heavy_atom_clash_proxy.frac_mean** 约 **0.00339→0.0146**；**`output.zip` 已变**。 | 见下行线上结果；**勿再提交**本包。 |
| 2026-05-19 22:04 | 用户提交 **`daima/202605192200`** 对应 **`output.zip`**（`sequence_prior` + P1/P2 **`fast-preview`** ColabFold PDB）：排行榜 **0.537492**（2026-05-19 22:04:10；相对基线 **0.700651** 约 **−0.163**）。 | **线上 A/B 强烈否定**：低 pLDDT（≈29）、无 MSA 的预览结构并入 **`prefer_sequence_prior`** 后拖垮 Base Score 与系综/物理子项；本地已出现的 P1 高 pairwise、高 clash 与线上一致。**日常冲榜回滚 lock / `daima/202605081315`**。 | ColabFold 仅作管线验证时**不要**默认 `--prefer-sequence-prior` 打包；合入前需 **MSA + 多模型** 且设 **pLDDT/长度** 门槛，或先小样本离线筛再 A/B；**勿提交** **`202605191345`** / **`202605182253`**。 |
| 2026-05-20 | **`build_sequence_prior_sources.py`** 默认 **`--min-mean-plddt 50`**；**`run_sequence_prior_pipeline.ps1`** 同步；**`watch_colabfold_and_archive.ps1`**；lock 已恢复 **`results/submission/output.zip`**。 | 现有 P1/P2 **`fast-preview`**（mean pLDDT≈29）合并时 **rejected**，`sequence_prior_candidates=0`，与 **0.700651** 等价；**未新建 `daima`**。 | 见下行执行序。 |
| 2026-05-20 | **执行序（已定）**：① 冲榜维持 **lock/0.700651**；② **P2 正式 MSA**（`predictions_msa/`，2 模型 3 recycle）← 已启动；③ **P3 正式 MSA**（P2 后）；④ **P1 正式 MSA**（最长，最后）。修复 E 盘损坏 **`params_model_5_ptm.npz`**（`check_colabfold_params.py`）。 | P3 `fast-preview` 曾因坏权重 **BadZipFile** 失败；**`--fast-preview` 不进提交**（pLDDT 门槛）。 | P2 监控：`results/colabfold/problem_2/watch_archive.log`；仅 pLDDT≥50 时自动 **`daima/YYYYMMDDHHMM`**。 |
| 2026-05-20 | **进行中**：P2 MSA 已拉通 ColabFold API（`p2.a3m` + `p2_env/`），MSA 超时后重试成功，CPU 推理进行中；**`queue_p3_after_p2_msa.ps1`** 后台排队 P3（`predictions_msa`）。 | 日志：`predictions_msa/log.txt`；队列：`results/colabfold/queue_p2_p3.log`。 | P2 完成后自动开 P3；P1 仍等 P2/P3 pLDDT 结果。 |
| 2026-05-20 | P2 **`2 模型×3 recycle`** 在 CPU 推理约 **40 min** 后进程退出（**无 PDB**，疑 WSL/OOM）；**MSA 已缓存**于 `predictions_msa/`。已改为 **`1 模型×3 recycle`** 同目录重跑并重启 watch/queue。 | 降模型数减内存；仍用完整 MSA（非 fast-preview）。 | 监控 `problem_2/watch_archive.log`；pLDDT≥50 才归档 A/B。 |
| 2026-05-21 11:52 | P2 **正式 MSA** 完成：`predictions_msa/p2_unrelaxed_...pdb`（**pLDDT=95.1**，3 recycle，约 **22.5 h** CPU）；preview PDB 被 **pLDDT 门槛拒绝**；**`run_sequence_prior_pipeline -Archive`** → **`daima/202605212031`**。 | **P2** 仅合入 MSA 先验；`pairwise_ca_rmsd_A.mean` 约 **2.59→19.87 Å**；P1/P3 与 lock 模板一致；**`output.zip` 已变**。 | 线上 A/B **`daima/202605212031`**（勿与 **`202605192200`** preview 包混淆）；**P3 MSA** 已在跑。 |
| 2026-05-21 22:24 | 用户提交 **`daima/202605212031`**：排行榜 **0.704636**（相对基线 **0.700651** 约 **+0.0040**）。 | **仅 P2** 主模板改为 **完整 MSA ColabFold**（pLDDT≈95）；P1/P3 与 lock 相同；非 preview 路径（**0.537492**）。涨分与 §1.3「序列条件候选」一致，幅度小属正常 plateau。 | 继续 **P2/P3 高质量 MSA**；P3 完成后 **`auto_finish_msa_pipeline`** 再 A/B。 |
| 2026-05-22 | **`daima/guidang`** 更新为当前最高分镜像（**`refresh_guidang.ps1`** ← **`daima/202605212031`**，score **0.704636**）；新增 **`configs/submission_sources.best.json`**。 | 冲榜/回滚以 **guidang** 为准；工作区 `results/submission` 已同步该包。 | 线上优于 **0.704636** 后再刷新 guidang。 |
| 2026-05-22 | P3 MSA 完成（pLDDT≈**94.8**）；**`run_sequence_prior_pipeline -Archive`** → **`daima/202605222030`**（P2+P3 序列先验，P1 仍模板）。 | P3 `pairwise` 本地约 **19.65 Å**；线上未超过 **0.704636**。 | 启动 **P1 MSA**。 |
| 2026-05-23～24 | **P1 MSA** 完成（pLDDT≈**88.8**，约 **21.7 h** CPU）；**`run_sequence_prior_pipeline -Archive`** → **`daima/202605241146`**（P1+P2+P3 全 MSA）。 | 用户线上 **0.717129**（2026-05-24 11:54:09）；相对 **0.704636** 约 **+0.0125**；已存入 **`daima/guidang`**。 | 下一小步：**ColabFold 3 models** 扩充候选（`run_colabfold_extra_models.ps1`）。 |
| 2026-05-24 | 以 **0.717129** 更新 **`readme` §1.3/§1.5**、**`refresh_guidang.ps1`** 默认源；修复 guidang→guidang 全量 robocopy 卡死（同路径跳过 mirror）；新增 **`run_colabfold_extra_models.ps1`**、**`auto_finish_extra_models_pipeline.ps1`**。 | 文档/脚本对齐新基线；**未改**当前 **`output.zip` 几何**（无新 rank PDB）。 | 后台补跑 **3 models×3 recycle** 后自动合并归档 A/B。 |

### 1.6 竞赛系综提分 Prompt（复制给代码助手 / 科研助手）

**基线（线上最高 0.717129，guidang / `daima/202605241146`）**：冲榜用 **`configs/submission_sources.best.json`** 或 **`sequence_prior.json`**（**`--min-mean-plddt 50`**）；上一档 **0.704636**（`daima/202605212031`）；历史 **0.700651** 见 **`daima/202605081315`**。红线见 §1.1，勿使用赛题私有 GT 或 MD 轨迹。

```text
你是本仓库的“竞赛构象系综”工程师。目标是在完全合规前提下提高线上排行榜分数。

已知基线：
- 线上分数：**0.700651**（2026-05-08 与 2026-05-07 两次提交 plateau）。
- 配置：configs/submission_sources.lock_ab_202605051709.json（与 public 对齐：P1/P3 hybrid 短键修复、侧链网格避碰、**hybrid_sidechain_record_passes=4**）。
- 可复现归档：**daima/202605081315**（整包代码与 `output.zip` / `local_eval.json` 等）。

任务：
1) 阅读 readme.md §1.1–§1.5 与 document/rull.md，确认拟议改动合规。
2) 相对基线只做“小步”改动：一次只改一类因素（候选来源、ColabFold 参数、合并顺序、diversity_filter、relaxation 开关等），并说明预期影响的是 Base Score 还是 Ensemble Quality。
3) 优先实施 §1.3 表格中“实现难度低–中”且与现有脚本衔接最好的项（例如：扩充 results/colabfold|boltz|chai 候选 → build_sequence_prior_sources.py → generate_submission.py）。
4) 若引入 ColabFold/AF2 多样构象，请显式设计：多 seed、MSA 子采样或列掩码（参见 Nat Commun 2024 subsampled AF2、Communications Biology 2025 AFsample2），并写明随机种子与命令行以便写入 agent.log 与 daima 归档。
5) 迭代策略：平时小步提交 readme §1.5 记录即可；**一旦本轮改动可能显著影响线上分数或 `output.zip` 几何**，必须在该次运行 **`generate_submission.py`（或等效打包）启动时刻**取本地时间 **`YYYYMMDDHHMM`**，跑通生成与本地评测后，用 **`python scripts/archive_run.py --timestamp YYYYMMDDHHMM`** 将相关代码与参赛结果数据写入 **`daima/YYYYMMDDHHMM/`**（无 `results/openmm` 时可用 `--run-dir results/submission`）。
6) 在 readme.md §1.5 增加一行优化记录；若有新的高性价比想法，写入 §1.3 对应条目的“优化灵感”子 bullet。

输出格式：
- 变更摘要（文件级）
- 风险评估（precision vs coverage、clash、运行时间）
- 建议的本地验收指标（对照基线 local_eval.json）
- 若尚未跑通，给出最小可执行命令序列（Windows PowerShell 兼容）
```

更完整的对话版（含文献关键词）见 **§5 — Prompt 13**。

---

## 2) 这个项目的本质是什么

蛋白质功能常由多个构象共同决定（开/关态、中间态、瞬时态）。  
“构象系综生成”的核心是：在给定序列、复合物或实验约束下，得到一组**物理合理且功能相关**的结构分布，并回答这些问题：

- 哪些构象最稳定（占据概率高）？
- 构象间如何转换（转移路径和时间尺度）？
- 哪些状态与结合位点/功能状态相关？

可落地的三条主线：

- **快速多样性生成**：AlphaFold2/3、Boltz、MSA 扰动、结构扰动
- **物理采样校正**：OpenMM/GROMACS 分子动力学（MD）、增强采样
- **动力学统计建模**：tICA + MSM/HMM，估计状态转移与平均首达时间（MFPT）

---

## 3) 如何开始启动（建议最小可行路径）

如果你当前仓库还没有代码，建议先按以下最小流程搭建：

### Step A. 明确一个具体任务

- 选 1 个蛋白（建议先用小体系，如 100-300 aa）
- 写清目标：例如“生成 apo 蛋白 10-50 个可分簇构象，并识别可能的开闭状态”

### Step B. 建立环境（建议）

- Python 3.10+
- 必备包：`biopython`、`mdtraj`、`MDAnalysis`、`numpy`、`scipy`、`scikit-learn`、`matplotlib`
- MD 引擎（二选一优先）：`openmm`（上手快）或 `gromacs`
- MSM 工具：`pyemma`（历史经典）/ `deeptime` / `msmhelper`

### Step C. 做一个端到端 demo

1. 获取初始结构（PDB 或 AlphaFold/Boltz 预测）
2. 生成多初始构象（MSA subsampling / 轻微结构扰动 / 多模型预测）
3. OpenMM 短程 MD（每条轨迹 10-50 ns，先小步跑通）
4. 轨迹特征化（RMSD、接触图、主成分/tICA）
5. 聚类 + MSM 建模，得到宏观状态及转移图
6. 产出结论图：自由能图、状态占比、代表构象、关键转移路径

### Step D. 定义“完成标准”

- 至少 3 个可解释状态（含代表构象）
- 至少 1 条可解释转移路径（含时间尺度/MFPT）
- 至少 1 个和功能假设相关的结构观察（如口袋开合）

---

## 4) 通过网络搜集资料的高效路线

先看综述，再看工具文档，再看复现实战教程。

### A. 综述与方法图谱（先读）

- [Beyond static structures: protein dynamic conformations modeling in the post-AlphaFold era](https://pmc.ncbi.nlm.nih.gov/articles/PMC12262120/)
- [Deep Generative Modeling of Protein Conformations: A Comprehensive Review](https://www.mdpi.com/2673-6411/5/3/32)

重点关注关键词：`MSA perturbation`、`diffusion/flow matching`、`ensemble emulator`、`IDP`、`physics consistency`。

### B. 工具与可执行教程（优先落地）

- OpenMM 入门：
  - [OpenMM Cookbook: Protein in Water](https://openmm.github.io/openmm-cookbook/latest/notebooks/tutorials/protein_in_water.html)
  - [OpenMM User Guide: Running Simulations](https://docs.openmm.org/development/userguide/application/02_running_sims.html)
- MSM 入门：
  - [PyEMMA Pentapeptide MSM 示例](https://www.emma-project.org/v2.5/generated/pentapeptide_msm.html)
  - [MSMBuilder 教程（概念流程清晰）](http://msmbuilder.org/legacy/tutorial.html)

### C. 新一代 AI 模型（按需）

- [Boltz GitHub](https://github.com/jwohlwend/boltz)
- [Boltz-1 论文（bioRxiv）](https://www.biorxiv.org/content/10.1101/2024.11.19.624167v1.full)
- [Boltz-2（bioRxiv）](https://www.biorxiv.org/content/10.1101/2025.06.14.659707)（结合亲和力与复合物；可作多模态候选来源）

---

## 5) 各环节可直接使用的 Prompt 套件

使用建议：把 `{}` 中变量替换成你的课题信息。  
可用于任意大模型（通用对话模型 / 代码模型 / 科研助手）。

### Prompt 01：课题定义与范围收敛

```text
你是计算结构生物学顾问。请将以下课题收敛为可执行研究任务：
课题：{课题描述}
目标蛋白/复合物：{目标}
资源限制：{GPU/CPU/时间}

请输出：
1) 研究问题（最多3个）
2) 最小可行实验（MVP）流程（1-2周）
3) 可量化验收指标（至少5条）
4) 失败风险与备选方案
```

### Prompt 02：文献检索策略生成

```text
请为“蛋白质构象系综生成”设计系统检索策略。
要求：
- 数据库：PubMed / bioRxiv / arXiv / Google Scholar
- 时间：近5年优先，保留经典文献
- 输出布尔检索式（中英各一版）
- 输出筛选标准（纳入/排除）
- 输出阅读优先级（综述 > 方法 > 案例）
```

### Prompt 03：技术路线选择（AI vs MD vs 混合）

```text
我想研究 {蛋白名} 的构象异质性。
请比较三条路线：
A) 仅AI多构象生成
B) 仅MD采样
C) AI+MD+MSM混合

请按“准确性、可解释性、算力成本、周期、可发表性”打分，并给出推荐方案与理由。
```

### Prompt 04：OpenMM 启动脚手架生成

```text
请生成一个可直接运行的 OpenMM Python 脚本模板，用于蛋白在水中NVT/NPT模拟。
输入：PDB文件路径
要求：
1) 自动补氢、加水、加离子
2) 能量最小化 + NVT平衡 + NPT生产
3) 输出 dcd 轨迹和 log
4) 参数集中到脚本顶部便于改动
5) 给出每一步的简短注释
```

### Prompt 05：轨迹特征工程方案

```text
给定蛋白MD轨迹，请设计“用于MSM建模”的特征工程流程。
请比较并选择：二面角、接触图、Cα距离、RMSD矩阵。
输出：
1) 推荐特征组合
2) 降维方法（PCA/tICA）及参数建议
3) 质量检查清单（采样充分性、特征稳定性）
```

### Prompt 06：MSM 建模与验证

```text
请给出从聚类轨迹到MSM的标准流程，并提供伪代码。
要求包含：
- 聚类策略（kmeans/其他）
- lag time 选择（ITS依据）
- Chapman-Kolmogorov 检验
- PCCA 宏观状态划分
- MFPT 与主通路计算
并给出常见失败模式及修复建议。
```

### Prompt 07：结果解释与生物学映射

```text
我有若干宏观状态及其占比、代表构象和转移速率。
请将这些结果映射到潜在功能机制：
- 哪些状态可能是活性/失活/中间态？
- 哪些结构区域主导转换（loop/domain/口袋）？
- 下一步可验证实验建议（突变、HDX、FRET、NMR）
```

### Prompt 08：图表与论文叙事生成

```text
请把我的构象系综结果整理成论文“Results”叙事框架。
输入：{关键结果}
输出：
1) 图1-图N建议（每图讲一个核心结论）
2) 每幅图的图注草稿
3) 结果段落提纲（按逻辑递进）
4) 可能被审稿人质疑的问题与回应
```

### Prompt 09：代码审阅与复现性检查

```text
请以“可复现计算生物学”标准审阅我的项目目录与脚本。
检查项：
- 环境锁定（requirements/conda）
- 随机种子与日志
- 参数配置外置化
- 数据版本与输入输出规范
- 一键复现实验入口（run.sh 或 Makefile）
输出：问题清单 + 修复优先级 + 最小修复补丁建议。
```

### Prompt 10：周报/导师汇报生成

```text
你是我的科研助理。基于以下工作记录生成周报：
本周完成：{内容}
关键结果：{结果}
问题与阻塞：{问题}
下一步计划：{计划}

请输出：
1) 300字摘要版
2) 1页PPT大纲版
3) 导师可能追问的5个问题与回答要点
```

### Prompt 11：讨论、局限与可证伪性

```text
基于当前构象系综与 MSM 结果，写 Discussion 提纲（不写空话）：
输入：{主要结论 + 已知局限}
输出：
1) 与文献一致/不一致之处（各举2条并给出文献或预印本线索）
2) 三条最强反对意见（采样不足、力场偏差、状态模型误设）及你方的数据回应
3) 明确写出“若出现何种新实验结果则推翻本结论”
4) 下一步最小实验（计算或湿实验）各一项
```

### Prompt 12：审稿人往返（多轮修改）

```text
模拟两轮审稿：
第一轮：以审稿人身份列出 Major/Minor 共≤8条，每条对应到文稿中的小节或图号。
第二轮：以作者身份逐条回复（接受/反驳+补实验/改表述），并给出修改后的段落或图注 diff 要点。
禁止：无证据的拔高与未标注的引用。
```

### Prompt 13：竞赛多构象提交（文献对齐，以锁版为基线）

```text
你是本仓库的竞赛构象系综工程师。输入为赛题 document/*.json 中的序列与公开规则 document/rull.md。

基线（勿在未记录 A/B 的情况下静默偏离）：
- 线上确认分数：**0.700651**（2026-05-08 13:36:49 与 2026-05-07 22:01:17  plateau）。
- 配置文件：configs/submission_sources.lock_ab_202605051709.json（与 public 对齐：P1/P3 hybrid 短键修复 + 侧链网格避碰 + **hybrid_sidechain_record_passes=4**）。
- 可复现归档目录：**daima/202605081315**（整包生成+归档快照；后续若有新快照以 §1.5 表末行为准）。

文献与数据处理约束（仅使用公开工具与公开数据；禁止赛题 GT / 私有 MD 轨迹）：
- MSA 子采样 / 降低共进化盆地偏置：Nat Commun 2024 subsampled AlphaFold2（https://www.nature.com/articles/s41467-024-46715-9）。
- 随机列掩码与多构象：Communications Biology 2025 AFsample2（https://www.nature.com/articles/s42003-025-07791-9）。
- 序列净化与多态采样：arXiv:2503.00165（https://arxiv.org/abs/2503.00165）。
- 超越纯 MSA 的结构采样：ConforFold（https://pmc.ncbi.nlm.nih.gov/articles/PMC13064411/）。
- Boltz-2 与 pair 表示上的构象探索：bioRxiv 2025.06.14.659707、2026.01.23 Boltz-sample steering（https://www.biorxiv.org/content/10.1101/2025.06.14.659707 与 https://www.biorxiv.org/content/10.64898/2026.01.23.701250v1.full-text）。
- 流匹配 / SE(3) 系综（BBFlow 等）：https://arxiv.org/abs/2503.05738
- 条件扩散与局域几何对齐（Mac-Diff）：https://link.springer.com/article/10.1038/s42256-026-01198-9
- 推理期优化以贴近实验系综：https://arxiv.org/abs/2602.24007
- 物理反馈对齐（EBA）：https://proceedings.mlr.press/v267/lu25b.html

请产出一份「下一步最小实施包」：
1) 从上述文献中选出 2–3 条最适合本仓库流水线（ColabFold/Boltz/Chai → build_sequence_prior_sources.py → generate_submission.py）的具体动作，并按「预期涨分幅度 × 实现难度」排序。
2) 为每条动作写出：所需输入目录、建议 CLI、随机种子策略、如何写入 agent.log / readme §1.5。
3) 明确哪些改动需要重新打包 output.zip 并归档 daima/YYYYMMDDHHMM（启动时刻命名）。
4) 若某条动作风险高（伤 precision 或 clash 上升），给出回滚开关（JSON 字段名级别）。

回答使用中文，条目化，避免空话。
```

（§1.6 为精简版；本 Prompt 为带链接的完整版，便于直接粘贴到大模型。）

---

## 6) 推荐目录结构（可按此初始化）

```text
Danbaizhi/
  data/
    raw/
    processed/
  configs/
  scripts/
    prepare_structure.py
    run_openmm.py
    analyze_features.py
    build_msm.py
  notebooks/
  results/
    figures/
    tables/
  docs/
  readme.md
```

---

## 7) 你现在就可以执行的第一步

1. 选定一个目标蛋白并写入 3 条研究问题  
2. 用 Prompt 01 和 Prompt 02 产出任务定义与检索式  
3. 用 Prompt 04 先跑通一个 OpenMM 最小模拟  
4. 用 Prompt 05 + 06 得到第一版 MSM 状态图  
5. 用 Prompt 07 + 08 输出第一版科学叙事  
6. **若当前任务是竞赛多构象提交**：以 §1.3 基线与 **Prompt 13** 驱动下一轮小步优化，并遵守 `daima/YYYYMMDDHHMM` 归档规则。

如果你愿意，我下一步可以直接继续为这个仓库生成：

- `scripts/run_openmm.py` 最小可运行脚本
- `scripts/build_msm.py` 的分析骨架
- `configs/default.yaml` 参数文件模板

---

## 8) 已生成的项目脚手架与使用方式

已创建：

- `configs/default.yaml`：统一参数配置（输入、OpenMM 参数、分析参数）
- `scripts/run_openmm.py`：最小可运行的 OpenMM 流程（补氢/加水/最小化/NVT/NPT）
- `scripts/build_msm.py`：完整 MSM 流程（特征、降维、聚类、ITS、CK、PCCA-like、MFPT）

### 7.1 安装建议

```bash
pip install pyyaml numpy scipy scikit-learn mdtraj
```

如果使用 OpenMM（推荐 conda）：

```bash
conda install -c conda-forge openmm
```

可选（做 tICA）：

```bash
pip install deeptime
```

### 7.2 准备输入文件

1. 将目标结构放到：`data/raw/input.pdb`  
2. 如路径不同，修改 `configs/default.yaml` 中 `input.pdb_path`

### 7.3 运行最小模拟

```bash
python scripts/run_openmm.py --config configs/default.yaml
```

输出目录（默认）：`results/openmm/`，包括：

- `traj.dcd`：轨迹
- `state.log`：状态日志
- `state.chk`：checkpoint
- `minimized.pdb` / `final.pdb`：最小化与最终构象

### 7.4 运行 MSM 前处理骨架

```bash
python scripts/build_msm.py --config configs/default.yaml
```

将生成（含完整 MSM 结果）：

- `features.npy`
- `embedding.npy`
- `state_assignments.npy`
- `transition_counts.npy` / `transition_matrix.npy`
- `macro_assignments.npy` / `macro_transition_matrix.npy`
- `macro_mfpt.npy`
- `msm_report.json`（ITS 扫描、CK 误差、宏观状态占比）
- `msm_report.json`（ITS 扫描、CK 误差、宏观状态占比 + 自动结论 `auto_summary`）

### 7.5 MSM 参数说明（`configs/default.yaml`）

- `analysis.msm.lagtime`：主模型 lag time
- `analysis.msm.lagtime_scan`：ITS 扫描的 lag 列表
- `analysis.msm.n_its`：输出前几个 implied timescales
- `analysis.msm.ck_multiples`：CK 检验倍数（对应 `k*lagtime`）
- `analysis.msm.pcca_nstates`：粗粒化宏观状态数（PCCA-like）

`msm_report.json` 中新增 `auto_summary` 字段，可直接用于周报/汇报，包括：

- `ck_quality`：CK 质量等级（good/fair/poor）
- `slow_process_timescales`：慢过程时间尺度摘要
- `dominant_macrostate_population`：主导宏观态占比
- `recommended_next_action`：下一步建议动作
- `conclusion_text`：可直接引用的一段结论文字

### 7.6 归档流程自动化（满足 `daima/YYYYMMDDHHMM` 规则）

归档脚本：`scripts/archive_run.py`

默认会归档以下内容到 `daima/<启动时间>/`：

- `scripts/`
- `configs/`
- `document/`
- `readme.md`
- `tests/`（若存在）
- `results/openmm/`
- `results/submission/`（含 `output.zip`）
- `data/public/`
- `manifest.json`（含 `submission_artifacts`、`timeline_output_zip`；补档后另有 **`supplement_log`**）
- **时间线根目录**：若存在 `results/submission/output.zip`，会再复制一份到 `daima/<启动时间>/output.zip`，便于按时间线直接取用提交包

最常用命令（自动生成当前时间目录）：

```bash
python scripts/archive_run.py
```

可选：指定目录名（必须是 `YYYYMMDDHHMM`）与备注：

```bash
python scripts/archive_run.py --timestamp 202605012205 --note "S1 1.5ns stable run"
```

可选：附加额外文件/目录：

```bash
python scripts/archive_run.py --extra-path data/processed --extra-path results/figures
```

对已存在的 **`daima/YYYYMMDDHHMM`** 补全遗漏目录或刷新提交产物（不新建时间戳目录）：

```bash
python scripts/archive_run.py --supplement daima/202605100102 --note "补齐 tests 与多工具目录" --extra-path tests --extra-path results/boltz --refresh-submission --refresh-timeline-zip
```

### 7.7 一键运行并自动归档（推荐）

管道脚本：`scripts/run_pipeline.py`  
执行顺序：`run_openmm.py -> build_msm.py -> archive_run.py`

最常用：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --archive-note "daily run"
```

如果只想在已有轨迹上重跑 MSM 并归档：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --archive-note "msm-only rerun"
```

可选：强制指定归档时间目录名：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --archive-timestamp 202605012210
```

### 7.8 初赛提交包自动生成（output.zip）

脚本：`scripts/generate_submission.py`  
功能：读取 `document/1.json`、`document/2.json`、`document/3.json`，生成：

- `{problem_id}_conf{N}_pred.cif`
- `agent.log`
- `output.zip`
- `strategy_report.json`（每题使用了哪种生成策略及原因）

执行命令：

```bash
python scripts/generate_submission.py --note "baseline submission package"
```

优先尝试轨迹代表帧（长度不匹配时自动回退 baseline）：

```bash
python scripts/generate_submission.py --strategy auto --traj-path results/openmm/traj.dcd --top-path results/openmm/final.pdb
```

按题号指定不同策略/轨迹来源（推荐）：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.example.json
```

`sources-config` 支持为每个 `problem_id` 指定：

- `strategy`：`baseline_ca` / `auto` / `trajectory_ca`
- `traj_path`：该题轨迹路径（可选）
- `top_path`：该题拓扑路径（可选）

默认输出目录：`results/submission/`

### 7.9 管道中一并生成提交包

在一键管道中加入 `--with-submission`：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --archive-note "submission build"
```

带每题来源配置的一键命令：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --submission-sources-config configs/submission_sources.example.json --archive-note "submission build with per-problem sources"
```

---

## 9) 完整执行 SOP（不遗漏步骤）

以下为从 0 到 `output.zip` 的完整闭环清单。按顺序执行可覆盖当前项目所有关键阶段。

### 9.1 阶段 A：环境与目录准备

1. 安装依赖：
   - `pip install pyyaml numpy scipy scikit-learn mdtraj openmm`
2. 确认目录存在：
   - `configs/`、`scripts/`、`document/`、`results/`、`daima/`
3. 确认赛题文件存在：
   - `document/1.json`、`document/2.json`、`document/3.json`

### 9.2 阶段 B：单体系验证（工程通路）

1. 配置 `configs/default.yaml`（输入结构、MD、MSM 参数）
2. 运行模拟：
   - `python scripts/run_openmm.py --config configs/default.yaml`
3. 运行分析：
   - `python scripts/build_msm.py --config configs/default.yaml`
4. 查看：
   - `results/openmm/msm_report.json`

### 9.3 阶段 C：参数迭代（稳定性提升）

1. 先调聚类数（如 50 -> 20 -> 15）
2. 再调 lag 与扫描窗口（`lagtime_scan`）
3. 若出现 NaN：
   - 优先将 `step_size_ps` 下调（如 0.004 -> 0.002）
4. 记录每轮指标：
   - 帧数、CK 误差、宏观态占比、慢过程 timescales

### 9.4 阶段 D：生成提交包（初赛格式）

1. 直接生成（baseline）：
   - `python scripts/generate_submission.py --note "baseline"`
2. 自动优先轨迹策略：
   - `python scripts/generate_submission.py --strategy auto`
3. 每题独立来源策略（推荐）：
   - 先编辑 `configs/submission_sources.example.json`
   - 再运行：`python scripts/generate_submission.py --sources-config configs/submission_sources.example.json`
4. 结果目录：
   - `results/submission/`

### 9.5 阶段 E：提交前自检（必须）

1. `output.zip` 存在且 `< 100MB`
2. 包内包含：
   - `1_conf*_pred.cif`
   - `2_conf*_pred.cif`
   - `3_conf*_pred.cif`
   - `agent.log`
3. 每题 conformer 数量 `<=10`
4. 查看 `strategy_report.json` 是否存在异常回退

### 9.6 阶段 F：归档（规则强制）

1. 运行归档：
   - `python scripts/archive_run.py --note "submission candidate"`
2. 检查归档目录：
   - `daima/YYYYMMDDHHMM/`
3. 确认 `manifest.json` 存在，且记录了代码和结果路径

### 9.7 阶段 G：一键串行执行（推荐日常）

1. 已有轨迹，仅分析+提交+归档：
   - `python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --archive-note "daily submission run"`
2. 含每题来源配置：
   - `python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --submission-sources-config configs/submission_sources.example.json --archive-note "daily submission run with sources"`

### 9.8 当前状态定义

- 已完成：工程链路、分析链路、提交包链路、归档链路
- 待持续优化：高质量构象来源（每题匹配轨迹/模型），以提升评分表现

---

## 10) 当前已执行结果与缺口清单

### 10.1 本次已执行（可复现）

- 已运行命令：
  - `python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --submission-sources-config configs/submission_sources.json --archive-note "candidate submission with current sources"`
- 已产出：
  - `results/submission/output.zip`
  - `results/submission/strategy_report.json`
  - `daima/202605012214/manifest.json`

### 10.2 当前缺口（影响得分）

- `strategy_report.json` 显示 3 个题目均回退为 `baseline_ca`
- 原因：当前可用轨迹长度为 76 aa，与题目序列长度（1104/889/891）不匹配

### 10.3 需要补充的数据（下一步必须）

为提升质量到“真实轨迹/结构驱动提交”，需你补充每题匹配来源：

- `problem 1`：与序列长度 1104 匹配的 `traj.dcd + final.pdb`
- `problem 2`：与序列长度 889 匹配的 `traj.dcd + final.pdb`
- `problem 3`：与序列长度 891 匹配的 `traj.dcd + final.pdb`

补充后只需两步：

1. 更新 `configs/submission_sources.json` 的每题路径  
2. 重新运行：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --submission-sources-config configs/submission_sources.json --archive-note "candidate submission with matched sources"
```

---

## 11) 公开数据库数据获取与整理（已执行）

已实现脚本：`scripts/prepare_public_data.py`  
数据源：`RCSB PDB` 序列检索 + 结构下载（公开数据库）

### 11.1 已执行命令

```bash
python scripts/prepare_public_data.py --problem-json-dir document --out-dir data/public --max-hits 20 --max-downloads 8
```

### 11.2 数据保存目录（主程序可访问）

- `data/public/summary.json`
- `data/public/problem_1/rcsb_hits.json`
- `data/public/problem_1/rcsb_structures/*.cif`
- `data/public/problem_2/rcsb_hits.json`
- `data/public/problem_2/rcsb_structures/*.cif`
- `data/public/problem_3/rcsb_hits.json`
- `data/public/problem_3/rcsb_structures/*.cif`

### 11.3 与主程序对接方式

新增配置：

- `configs/submission_sources.public.json`

可直接运行：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.public.json --note "public template cif integration"
```

或在管道中运行：

```bash
python scripts/run_pipeline.py --config configs/default.yaml --skip-openmm --with-submission --submission-sources-config configs/submission_sources.public.json --archive-note "public-db integrated run"
```

### 11.4 当前匹配情况（基于 `strategy_report.json`）

- Problem 2：已成功使用 `template_cif`（长度完全匹配）
- Problem 1 / 3：可使用 `template_align`（序列对齐映射 + 缺口插值）

说明：这不影响流程可用性，但会影响评分上限。后续可继续扩大检索范围或引入序列对齐裁剪策略提升匹配率。

### 11.5 对齐映射策略（已接入主程序）

`generate_submission.py` 已新增 `template_align` 策略：

- 对模板序列与目标序列做全局比对（Needleman-Wunsch）
- 将模板 CA 坐标映射到目标长度
- 对目标中的缺口位点做线性插值/端点外推

推荐配置：`configs/submission_sources.public.json`

- Problem 1：`template_align` + `2PO4.cif`
- Problem 2：`template_cif` + `3EBG.cif`
- Problem 3：`template_align` + `2VCA.cif`

验证命令：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.public.json --note "template align validation"
```

当前验证结果（`results/submission/strategy_report.json`）：

- Problem 1：`template_align`，`mapped=1094/1104`
- Problem 2：`template_cif`，长度完全匹配
- Problem 3：`template_align`，`mapped=887/891`

### 11.6 提交得分为 0.0 的常见原因与已做修复

赛题要求「完整原子三维坐标」且需通过物理合理性检查；仅手写 **CA-only** mmCIF 时，系综多样性、clash、Ramachandran 等子项可能极差或解析失败，易出现 **0 分**。

已更新 `scripts/generate_submission.py`：

- **长度与题目一致**的模板（如 Problem 2）：默认用 `mdtraj` 导出 **全原子** mmCIF（`save_cif`），并支持 `template_cifs` 多文件做多构象；每构象带小幅刚体扰动以增加多样性。
- **CA 路径**（align / baseline）：对 CA 链做 **3.8 Å 间距修复** + **小幅刚体扰动**，减轻共线/重叠导致的非物理结构。

配置见 `configs/submission_sources.public.json`（Problem 2 为整链等长 **mdtraj 全原子**；Problem 1/3 为 **`template_align` + 多模板 + 混合全原子** 见 §11.9）。重新生成提交包：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.public.json
```

### 11.7 本地弱评测（`scripts/eval_submission_local.py`）

在无法访问官方评测时，可对 `output.zip` 做 **CA 系内检查**：解压后逐题读取 `{id}_conf*_pred.cif`，对照 `document/{id}.json` 序列长度；输出 **pairwise CA-RMSD（Å）**、**CA 键长步距（nm）**、**粗 clash 占比**（非相邻 CA 过近比例）。结果写入 `results/submission/local_eval.json`（可用 `--out-json` 改路径）。

```bash
python scripts/eval_submission_local.py --zip results/submission/output.zip
```

生成提交包时可顺带跑一遍（写入 `results/submission/local_eval.json`，可用 `--eval-out-json` 改路径）：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.public.json --with-local-eval
```

整条流水线：`python scripts/run_pipeline.py --with-submission --with-local-eval --submission-sources-config configs/submission_sources.public.json`（需与 `--with-submission` 同时使用）。

若你本地另有 **GT mmCIF**（文件名形如 `1_*.cif`、`2_*.cif`，放在同一目录），可加 `--gt-dir <目录>`，脚本会按赛题 `Coverage / Precision` 定义用 **Kabsch CA-RMSD** 近似 `base_score`（**不含**官方系综质量项；与线上分数可能仍有差距）。

### 11.8 Windows：`python` 仍打开商店或报找不到命令

系统 **Machine** PATH 里的 `...\Microsoft\WindowsApps` 会优先于用户 PATH 里的真实 `python.exe`。任选其一即可：

1. **设置**：应用 → 高级应用设置 → **应用执行别名** → 关闭 **python.exe** / **python3.exe**（推荐，无需改系统 PATH）。
2. **管理员一次性写入 Machine PATH**：以管理员打开 PowerShell，执行仓库内 `scripts/windows_prepend_python_machine_path.ps1`（脚本内已写死路径 `...\Python313`；执行后**重启终端与 Cursor**）。
3. 临时绕过：使用 **`py -3`**，或完整路径 `C:\Users\Lee\AppData\Local\Programs\Python\Python313\python.exe`。

### 11.9 多模板、`template_align` 混合全原子、可选 ColabFold

符合 `document/rull.md`：**仅基于序列**与**公开结构**（如 RCSB）建模；不得使用赛题私有 GT/轨迹。

- **`template_cifs`**：在 `configs/submission_sources.public.json` 中为每题列出多个 mmCIF；`template_align` 时 **每个 conformer 轮换一个模板** 做序列比对与 CA 对齐，提高系综多样性。
- **混合全原子（`align_hybrid_full_atom`）**：当 `full_atom: true` 且模板 CA 数与赛题序列长度差在 **`full_atom_max_slip`**（默认 48）以内时，对 **比对上的残基** 将模板全原子经 **Kabsch（CA）** 刚体变换到目标 CA 骨架；**未比对上的位点** 用近似 **ALA 主链+CB** 填充，以满足 mmCIF 全链坐标与物理检查的可解析性（侧链精度仍依赖模板覆盖度）。
- **链选择**：多链 mmCIF 自动选取 **CA 数最接近赛题长度** 的蛋白链。
- **可选 ColabFold**（FAQ 允许 AlphaFold 类起点）：`python scripts/run_colabfold_optional.py`（未安装 `colabfold_batch` 时安全跳过）。安装 [LocalColabFold](https://github.com/YoshitakaMo/localcolabfold) 或设置环境变量 **`COLABFOLD_BATCH`** 指向 `colabfold_batch` 可执行文件；预测结果写入 `results/colabfold/problem_{id}/`，再在 JSON 里将 `template_cif` / `template_cifs` 指到生成的 `.pdb` / `.cif` 即可接入当前提交流程。

### 11.10 论文与技术报告增强（GitHub 参考 + 方案 A：仅文档约定 HTTP）

**与 `document/rull.md` 的关系**：初赛提交要求 **`output.zip` + `agent.log`** 中的研发 Trace；**不要求**本仓库提供 HTTP 评测接口。官方评测返回的 JSON（`score` / `success` / `errorMsg` 等）描述的是**评测端**，不是参赛代码必须实现的 API。

#### 开源论文/科研智能体（方法论参考，按需阅读其 README 与流程图）

- [Galaxy-Dawn/claude-scholar](https://github.com/galaxy-dawn/claude-scholar)：全流程科研助理（文献—实验—写作分工与工具链）。
- [TobiasBlask/open-paper-machine](https://github.com/TobiasBlask/open-paper-machine)：分阶段写作与人机检查点。
- [PaperDebugger/paperdebugger](https://github.com/PaperDebugger/paperdebugger)：Research → Critique → Revision 式多轮修改。
- [federicodeponte/opendraft](https://github.com/federicodeponte/opendraft)：多 Agent 长文草稿与引用核验思路（本仓库若不做联网检索，须在正文声明引用来源与核验状态）。

#### 提升文稿质量的落地做法（与本仓库 Prompt 01–12 配套）

- 图—结论一一对应；Methods 写清数据与命令；Discussion 写满局限与可证伪条件（见 Prompt 11）。
- 用 Prompt 12 做审稿往返，避免“一次性生成即定稿”。

#### 方案 A：若将来为内部服务增加 HTTP（自愿，非赛题硬性）

- 业务失败时 **HTTP 状态码不得为 200**（客户端问题用 4xx，服务端异常用 5xx）。
- 响应体建议统一为：

```json
{
  "error": {
    "code": "STRING_MACHINE_READABLE",
    "message": "HUMAN_READABLE_DETAIL",
    "requestId": "OPTIONAL_CORRELATION_ID"
  }
}
```

- 离线 CLI 或无请求上下文时，`requestId` 可为空字符串或省略；与官方评测返回字段无强制对齐关系。
- 本地自检：函数 **`validate_agent_log_paper_readiness`** 定义在 `scripts/generate_submission.py`（需用 `importlib` 按路径加载该脚本后调用，见 `tests/test_agent_log_paper_readiness.py`）；或直接跑 **§13.4** 的 `unittest` 命令验证生成逻辑。

### 11.11 锁版提交复现（A/B 结论：仅 P1 开筛选，P3 关，P2 不变）

**历史**：与归档 **`daima/202605051709`** 对齐的初版锁文件仅含 diversity 与 hybrid 全原子对齐，不含短键修复与侧链避碰。  
**当前（线上新基线 0.700651，2026-05-08 起）**：**`configs/submission_sources.lock_ab_202605051709.json`** 与 **`configs/submission_sources.public.json`** 对齐（P1/P3：`repair_hybrid_short_ca`、`relieve_hybrid_sidechain_clashes`、**`hybrid_sidechain_record_passes=4`** 等）。与排行榜 **0.700651** 对应的整包快照见 **`daima/202605081315`**（更早全量快照仍含 **`daima/202605081254`**）。日常实验仍优先改 `public.json`，确认线上更优后再同步锁版。

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.lock_ab_202605051709.json --with-local-eval --note "lock repro aligned public hybrid+sidechain"
python scripts/archive_run.py --timestamp YYYYMMDDHHMM --note "lock repro aligned public hybrid+sidechain"
```

---

## 12) 可汇报产出（基于本次实跑结果）

本节为当前阶段的“可直接汇报版本”，对象蛋白为 `1UBQ`，流程为 `OpenMM -> MSM`。

### 12.1 实验运行记录（关键轮次）

| 轮次 | MD 参数（核心） | MSM 参数（核心） | 关键结果 |
| --- | --- | --- | --- |
| 冒烟测试 | `dt=0.004 ps`, `nvt=500`, `npt=1000` | `clusters=10`, `lag=2` | 帧数少（15），CK 很差，仅用于流程验证 |
| 短程测试 | `dt=0.004 ps`, `nvt=10000`, `npt=40000` (~0.2 ns) | `clusters=30`, `lag=5` | 能跑通，但宏观态偏塌缩 |
| 1 ns 基线 | `dt=0.004 ps`, `nvt=10000`, `npt=240000` | `clusters=50`, `lag=10` | 帧数 250，但 CK 误差高，宏观态几乎单峰 |
| 参数优化 P1 | 不重跑 MD（沿用 1 ns） | `clusters=20`, `lag=10` | CK 明显下降，宏观态更均衡 |
| 参数优化 P1.5 | 不重跑 MD（沿用 1 ns） | `clusters=15`, `lag=10` | CK 继续下降，状态分布稳定性提升 |
| 稳定采样 S1 | `dt=0.002 ps`, `nvt=10000`, `npt=740000` (~1.5 ns) | `clusters=15`, `lag=10` | 当前最佳：帧数 750，CK 进一步改善 |

> 说明：2 ns 尝试在 `dt=0.004 ps` 条件下触发 `Particle coordinate is NaN`，已通过降步长至 `0.002 ps` 修复。

### 12.2 当前最佳结果（S1）

来自 `results/openmm/msm_report.json` 的关键指标：

- `n_frames = 750`
- `ck_mean_error = 0.782`（较 1 ns / 15 clusters 的 `1.024` 继续下降）
- 慢过程时间尺度（`lag=10`）：`105.86, 91.74, 36.57, 22.73, 15.56`
- 宏观态占比：`0.480 / 0.351 / 0.169 / 0.000`

解释要点：

- 采样长度增加（250 -> 750 帧）后，慢过程时间尺度被更充分分离；
- CK 误差持续下降，说明 Markov 近似在当前设置下趋于稳定；
- 仍存在一个宏观态占比近零，提示当前粗粒化维度/状态数仍可优化。

### 12.3 300 字周报摘要（可直接提交）

本周完成了蛋白质构象系综生成流程的端到端落地，使用 1UBQ 建立了 OpenMM + MSM 的可复现实验链路。先后完成冒烟测试、0.2 ns、1 ns 和 1.5 ns 稳定采样，并在固定轨迹上进行了聚类参数优化（50→20→15）。结果显示，随着采样长度提升与状态离散度降低，模型稳定性持续改善：CK 均值误差由 2.91 降至 1.25、再降至 1.02，最终在 1.5 ns 条件达到 0.782；慢过程时间尺度在 lag=10 下达到 105.86、91.74、36.57 等较清晰分离值。过程中曾出现 2 ns 运行 NaN 崩溃，已通过将积分步长从 0.004 ps 降至 0.002 ps 解决。当前版本已可用于阶段汇报，但宏观态仍有近零占比状态，提示后续需继续优化特征与粗粒化策略，并建议追加更长采样（2-3 ns）验证收敛性。

### 12.4 1 页 PPT 大纲（导师汇报）

- 研究目标：从单结构预测转向构象系综与动力学建模
- 技术路线：OpenMM 采样 + MSM 状态建模（ITS/CK/PCCA-like/MFPT）
- 实验进展：冒烟 -> 0.2 ns -> 1 ns -> 1.5 ns（稳定版）
- 关键指标变化：帧数提升、CK 误差下降、慢过程时间尺度分离增强
- 异常与修复：2 ns NaN -> 降步长 0.004 ps 到 0.002 ps
- 当前结论：流程稳定可复现，统计质量显著提升但未完全收敛
- 下周计划：延长到 2-3 ns + 二面角特征对照 + 宏观态数扫描

### 12.5 导师可能追问与回答要点（5 条）

1) 为什么 CK 仍是 `poor`？  
答：当前阈值偏严格且状态模型仍有稀疏态，虽然评级未变，但误差已从 2.91 降到 0.782，趋势明确改善。

2) 为什么要从 50 类降到 15 类？  
答：高离散度在有限采样下导致转移矩阵稀疏，降簇可提升计数统计稳定性，实测 CK 与宏观态分布均改善。

3) NaN 是否说明模型无效？  
答：不是。NaN 属于数值积分稳定性问题，已通过减小步长修复并在 1.5 ns 成功复现。

4) 现在能否得出生物学结论？  
答：可给出“候选慢过程与状态占比”级别结论；机制级结论需更长采样和实验映射验证。

5) 下一步最优投入点是什么？  
答：先延长采样至 2-3 ns 并做 `ca_distance` vs `backbone_dihedral` 对照，收益最大。

### 12.6 下一步执行计划（可直接排期）

- 任务 1：在当前稳定参数下追加 `2-3 ns` 采样（优先）
- 任务 2：固定同一轨迹，运行 `backbone_dihedral` 特征 MSM 对照
- 任务 3：扫描 `pcca_nstates`（3/4/5）与 `lagtime`（10/20/40）稳定区间
- 任务 4：整理三张核心图（ITS、CK 误差曲线、宏观态占比）

---

## 13) 变更记录：论文增强（方案 A）与验证

### 13.1 改了什么

- **`readme.md`**：新增 Prompt **11**（讨论/局限/可证伪）、Prompt **12**（审稿人往返）；新增 **§11.10**（GitHub 参考、文稿质量要点、**方案 A** 下 HTTP 错误 JSON 约定及与 `document/rull.md` 的边界说明）。
- **`scripts/generate_submission.py`**：`agent.log` 增加 **Stage 5**（论文/技术报告与赛题审计对齐的自检要点）与 **Stage 6**（可选 HTTP 的自愿约定）；新增 **`validate_agent_log_paper_readiness`**，失败时返回 `{"success": false, "error": {"code", "message", "requestId"}}`（离线时 `requestId` 为空字符串）。
- **`tests/test_agent_log_paper_readiness.py`**：`unittest` 覆盖 **1 个失败**（缺标题的日志）与 **1 个成功**（调用 `_build_agent_log` 后校验通过）。

### 13.2 为什么

- 赛题在 `document/rull.md` 中强调 **agent.log** 的文献—代码—实验 Trace 与「论文式说明」能力；对照高星开源论文智能体的共同模式（分阶段、审稿循环、声明局限）提升可写性与可审计性。
- **方案 A**：赛题交付物为 **ZIP + agent.log**，不要求参赛仓库实现 HTTP；HTTP 约定仅作文档以便将来若封装服务时一致。

### 13.3 影响范围

- **CLI 参数与 `output.zip` 内文件名**：未改。
- **依赖**：未增加；测试使用标准库 **`unittest`**。
- **重新生成提交包**后，`agent.log` 会多出 Stage 5/6 段落；旧日志若需通过 `validate_agent_log_paper_readiness`，须重新运行 `generate_submission`。

### 13.4 验证结果

在项目根目录执行：

```bash
python -m unittest discover -s tests -p "test_*.py"
```

以及（可选）重新打包：

```bash
python scripts/generate_submission.py --sources-config configs/submission_sources.public.json
```

#### 建议提交信息（Conventional Commits）

- `docs: paper prompts, GitHub refs, and HTTP error envelope (option A)`
- `feat: agent.log paper audit stages and offline log validator`
- `test: agent log paper readiness success and failure`
