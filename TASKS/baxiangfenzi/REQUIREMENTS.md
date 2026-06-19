# baxiangfenzi — 需求摘要

## 任务

靶向分子生成 + 对接 + 逆合成路线规划 Agent。

## 输入

`/saisdata/37/target1.pdb`, `target2.pdb`, `target3.pdb`

## 输出

`result.zip`：`result1.csv`, `result2.csv`, `result3.csv`（mol_smiles + 逆合成路线 `>>`）

## 评分

官方权重：**0.7 × 分子质量 + 0.3 × 路线**（Sprint1 已接入 `score_route`）

## 详细赛题

`documen/Baxiangfenzi/readme.md`
