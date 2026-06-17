# 最高分存档 (cundang)

各赛道**固定目录**，只保留历史最高分对应的代码快照。出现更高分时**整目录替换**（旧代码删除，非追加）。

与 `guidang/` 的区别：

| | `cundang/<track>/` | `guidang/YYYYMMDDHHMM/<track>/` |
|--|-------------------|-----------------------------------|
| 命名 | 按赛道固定 | 按评分时间 |
| 内容 | 仅当前最佳 | 每次出分都留一份 |
| 更新 | 新分 > `best.json` 才替换 | 每次归档都追加 |

## 目录

| 赛道 | 固定路径 | 当前最佳 (`best.json`) |
|------|----------|------------------------|
| DrugClip | `drugclip/` | **19.23** (202605252202) |
| 神经算子 | `shenjingsuanzi/` | **57.69** (202605201228) |
| 靶向分子 | `baxiangfenzi/` | **0.667** (202606160717) |
| 蛋白质 | `danbaizhi/` | **0.717** (202606160717) |

## 更新命令

与 guidang 同一条命令，脚本会自动判断是否替换 cundang：

```powershell
py -3 scripts/archive_competition.py `
  --stamp 202606170549 `
  --track shenjingsuanzi `
  --score 42.090454 `
  --note "FNO1d agent" `
  --git-commit 1266385
```

输出示例：

- `cundang -> ... replaced best 32.900000 -> 42.090454` — 已替换
- `cundang -> ... kept best 57.685109 (new 42.090454)` — 未超过历史最佳，跳过

## 文件说明

```
cundang/<track>/
  best.json          # 进 Git：分数、时间戳、commit、说明
  submit/tracks/...  # 仅本地：该次最佳代码快照
```
