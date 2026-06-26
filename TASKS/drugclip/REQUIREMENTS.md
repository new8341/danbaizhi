# drugclip — 需求摘要

## 任务

DrugCLIP 虚拟筛选 Agent：自动优化 Mean **EF1%**（早期富集因子）。

## 输入

镜像内 `/app/benchmark`（117 任务，DUD-E + LIT-PCBA）

## 输出

`result.zip`：`result.csv`（ligand_id, score）+ `result.log`

## Agent 四阶段

理解论文/代码 → 诊断瓶颈 → 改代码/策略 → 干实验迭代

## 详细赛题

`documen/DrugClip/readme.md`

## 目标

超越当前 native agent **18.82**；冠军参考 **~19.23**（ReDrugClip hybrid_max_qed）
