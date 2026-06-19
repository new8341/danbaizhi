# danbaizhi — 需求摘要

## 任务

蛋白质构象系综生成：给定序列 JSON，输出多构象 mmCIF 代表集 + `agent.log`。

## 输入

`/saisdata/1.json`, `2.json`, `3.json`（氨基酸序列）

## 评分（初赛）

`Total = 0.5 × Base + 0.5 × Ensemble Quality`

- Base：CA-RMSD Coverage + Precision
- Ensemble：多样性、PCA、clash/Ramachandran 等

## 合规

- 不得使用私有 GT / MD 轨迹
- 可用公开 PDB、ColabFold/AF 等基于**题目序列**的预测

## 详细赛题

- `documen/fusai.md`
- `documen/Danbaizhi/`（样例 JSON）

## 实现目标

线上参考 **0.717129**（MSA ColabFold 先验 + hybrid 管线）
