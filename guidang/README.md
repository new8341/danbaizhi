# 按时间归档 (guidang)

每次天池评分后，将**该次代码 + 分数元数据**归档到以评分时间命名的目录。**只追加，不删除**历史目录。

```
guidang/YYYYMMDDHHMM/<track>/
  score_meta.json    # 进 Git
  submit/tracks/...  # 仅本地代码快照
```

## 与 cundang 的关系

- **guidang**：记录每一次出分（涨分、跌分、持平都归档）
- **cundang**：固定目录，仅保留该赛道**历史最高分**代码；更高分才替换（见 `cundang/README.md`）
- **SUBMISSIONS/**：框架逻辑别名，说明见 `SUBMISSIONS/README.md`
- **TASKS/*/EXPERIMENTS.md**：归档时自动追加实验行

同一条归档命令同时写 guidang；cundang 由脚本按分数自动决定是否替换。

## 示例

```powershell
cd h:\Fusai
py -3 scripts/archive_competition.py `
  --stamp 202606170549 `
  --track shenjingsuanzi `
  --score 42.090454 `
  --note "FNO1d agent Q2=39.7" `
  --git-commit 1266385
```

`--git-commit` 填镜像 `build_info.json` 中的 commit，确保快照与实际上分代码一致。

## 批量归档（2026-06-16 复赛首通）

```powershell
py -3 scripts/archive_competition.py --stamp 202606160708 --track drugclip --score 0.0 --note "RDKit简化agent" --git-commit 2977109
py -3 scripts/archive_competition.py --stamp 202606160716 --track shenjingsuanzi --score 32.904013 --note "KS baseline" --git-commit 65d41a9
py -3 scripts/archive_competition.py --stamp 202606160717 --track baxiangfenzi --score 0.666884 --git-commit 8c87d20
py -3 scripts/archive_competition.py --stamp 202606160717 --track danbaizhi --score 0.717129 --git-commit 2977fa8
```
