# 提交规则

## 天池每日提交次数（复赛，以平台当前显示为准）

| 赛道 | 每日可提交次数 | 镜像 tag | 输出 |
|------|----------------|----------|------|
| **shenjingsuanzi** | **1** | `.../shenjingsuanzi:0.1` | `/saisresult/submission.zip`（四 HDF5 A+B） |
| **baxiangfenzi** | **2** | `.../baxiangfenzi:0.1` | `/saisresult/result.zip` |
| **danbaizhi** | **2** | `.../danbaizhi:0.1` | `/saisresult/submission.zip` |
| **drugclip** | **2** | `.../drugclip:0.1` | `/saisresult/result.zip` |

- 次数按**自然日**重置；用完后需等次日再提。
- 每次提交消耗 1 次额度，与是否涨分无关。
- 镜像截止时间：**2026-06-29 14:00**（见 `documen/fusai.md`）。

## 复赛总成绩规则（摘要）

来源：`documen/fusai.md`

1. 至少参加 **2 个赛道**，否则不参与排名。
2. 各赛道原始分 **x** 独立换算 z-score：`z = (x - μ) / σ`。
3. **复赛总成绩 = 所参加赛道中 z-score 最高的两个之和**（只取 top-2）。
4. 总成绩排名前 **6** 晋级决赛。

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
| shenjingsuanzi | `.../shenjingsuanzi:0.1` | `submission.zip` → **4** HDF5（KS/cylinder × A/B） |

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
