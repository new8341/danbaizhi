# 存档说明 (cundang)

各赛道**当前最高分**对应代码的快照。当新提交分数超过 `best.json` 中的 `score` 时，运行归档脚本自动更新。

## 目录

| 赛道 | 目录 | 复赛得分 | 历史最佳 |
|------|------|----------|----------|
| DrugClip | `drugclip/` | 0.0 (2026-06-16) | **19.23** 初赛 ReDrugClip hybrid_max_qed |
| 神经算子 | `shenjingsuanzi/` | 32.90 (2026-06-16) | **57.69** 初赛 pdeburgers |
| 靶向分子 | `baxiangfenzi/` | **0.667** (2026-06-16) | 0.667 |
| 蛋白质 | `danbaizhi/` | **0.717** (2026-06-16) | 0.717 |

## 更新命令

```powershell
py -3 scripts/archive_competition.py --stamp 202606160717 --track danbaizhi --score 0.717129 --note "复赛 Docker 首通"
```

每次跑模型归档到 `guidang/YYYYMMDDHHMM/<track>/`（分数时间戳目录）。
