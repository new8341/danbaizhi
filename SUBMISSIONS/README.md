# 提交归档（SUBMISSIONS）

本目录为 **逻辑别名**，物理归档仍在仓库根目录：

| 框架名 | 实际路径 | 内容 |
|--------|----------|------|
| SUBMISSIONS | `guidang/YYYYMMDDHHMM/<track>/` | 每次出分的代码快照 + `score_meta.json` |
| best 版本 | `cundang/<track>/` | 仅保留最高分代码 + `best.json` |

## 写入方式

```powershell
py -3 scripts/archive_competition.py --stamp YYYYMMDDHHMM --track <track> --score <float> --git-commit <sha>
```

## 不再使用

- **`daima/` 新写入已废弃**（历史 `daima/` 与 `Project/daima/` 只读保留）
- 新实验统一：`guidang` + `TASKS/<track>/EXPERIMENTS.md`

## 本地 submission 样例

- `submit/danbaizhi/submission.zip`
- `submit/danbaizhi/manifest.json`
