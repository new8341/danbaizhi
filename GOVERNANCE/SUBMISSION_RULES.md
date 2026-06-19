# 提交规则

## 天池 Docker 契约（四赛道通用）

| 项 | 约定 |
|----|------|
| 入口 | `/app/run.sh` |
| 输入 | `/saisdata`（DrugClip：benchmark 在 `/app/benchmark`） |
| 输出 | `/saisresult/<output_name>` |

## 各赛道输出

| 赛道 | 镜像 | 输出文件 |
|------|------|----------|
| drugclip | `.../drugclip:0.1` | `result.zip` → `result.csv` + `result.log` |
| baxiangfenzi | `.../baxiangfenzi:0.1` | `result.zip` → `result1/2/3.csv` |
| danbaizhi | `.../danbaizhi:0.1` | `submission.zip` → mmCIF + `agent.log` |
| shenjingsuanzi | `.../shenjingsuanzi:0.1` | `submission.zip` → HDF5 ×2 |

Registry 前缀：`crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/`

## 发布流程

```powershell
pytest submit/tests/
py -3 VALIDATION/check_structure.py
# 可选：py -3 VALIDATION/check_submission.py --track danbaizhi --zip submit/danbaizhi/submission.zip
.\submit\publish_track.ps1 -Track danbaizhi
```

## 出分后归档

```powershell
py -3 scripts/archive_competition.py `
  --stamp 202606191200 `
  --track danbaizhi `
  --score 0.717129 `
  --note "描述" `
  --git-commit 2977fa8
```

## 禁止

- 自动向天池填表提交
- `-UnifiedTag` 或 `release-v0.1` 四仓联动构建
- 将私有评测 GT 写入仓库
