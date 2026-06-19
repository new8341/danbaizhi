# danbaizhi — 经验教训（摘要）

> 完整版：`Project/经验教训.md`（867 行，含 Prompt 模板）。本节为 AI 优化必读摘要。

## 核心判断

1. **涨分主杠杆是 Base Score**：高质量、序列相关的多样构象，而非只调 `diversity_filter` 或侧链网格。
2. **低质量 preview 会大幅掉分**：`fast-preview` / 低 pLDDT（~29）进入提交链 → 0.537（较 0.70 **−0.16**）。
3. **本地 proxy ≠ 线上分**：重大策略必须线上 A/B，并归档 guidang + `--git-commit`。
4. **平台期微调无效**：侧链轮数 3→4 等只改 clash proxy，分数卡在 ~0.7006。

## 踩坑清单

| 问题 | 处理 |
|------|------|
| 首提 0 分 | 全原子 mmCIF；`template_align` 避免共线 CA |
| P1 diversity 加大无效 | 改**候选来源**（序列先验），非只调 multiplier |
| ColabFold 无 Windows 原生 | WSL2 + `Project/scripts/start_danbaizhi_a1.ps1` |
| 权重占满 WSL 盘 | `COLABFOLD_WSL_XDG_CACHE` → `Project/data/colabfold_xdg_cache` |
| 长跑无 ETA | 看 `_logs/*.err.log`、`.pdb` 产物，勿用 chat 推断 |

## 归档约定（已更新）

- **新归档**：`guidang/` + `cundang/` + 本 EXPERIMENTS 表
- **不再新建 `daima/`**（历史只读）
- 冲榜配置：`Project/processed_data/configs/submission_sources.json` / best 锁版

## 分数里程碑

| 阶段 | 分数 | 含义 |
|------|------|------|
| 早期 | ~0.19 | 格式/全原子未就绪 |
| 2026-05-05 | 0.700463 | 可评测全原子流程 |
| 2026-05-21~24 | **0.717129** | MSA + pLDDT 过滤有效涨分 |

## 一句话

竞赛侧从格式合规到序列条件多模型先验的跃迁证明：**涨分靠高质量多样构象，不是局部调参**；Windows+WSL+ColabFold 基础设施可复用。
