# 归档说明 (guidang)

每次天池评分后，将**相关代码 + 分数元数据**归档到以评分时间命名的目录：

```
guidang/YYYYMMDDHHMM/<track>/
  score_meta.json
  submit/tracks/...
  ...
```

## 批量归档示例（2026-06-16 复赛首通）

```powershell
cd h:\Fusai
py -3 scripts/archive_competition.py --stamp 202606160708 --track drugclip --score 0.0 --note "RDKit简化agent，日志审核置零"
py -3 scripts/archive_competition.py --stamp 202606160716 --track shenjingsuanzi --score 32.904013 --note "KS baseline + P2 sample fallback"
py -3 scripts/archive_competition.py --stamp 202606160717 --track baxiangfenzi --score 0.666884
py -3 scripts/archive_competition.py --stamp 202606160717 --track danbaizhi --score 0.717129
```

`cundang/` 仅在分数超过历史最佳时自动更新（见 `cundang/README.md`）。
