# 项目索引（AI 必读）

## 仓库

| 项 | 值 |
|----|-----|
| GitHub | `new8341/danbaizhi` |
| 本地根 | `H:\Fusai` |
| 大赛规则 | `documen/fusai.md` |

## 四赛道映射

| 任务 | track 名 | 代码 | 文档 |
|------|----------|------|------|
| 1 DrugClip | `drugclip` | `submit/tracks/drugclip_agent/` | `TASKS/drugclip/` |
| 2 靶向分子 | `baxiangfenzi` | `submit/tracks/baxiangfenzi_agent/` | `TASKS/baxiangfenzi/` |
| 3 蛋白质构象 | `danbaizhi` | `Project/code/` + `submit/tracks/danbaizhi.py` | `TASKS/danbaizhi/` |
| 4 神经算子 | `shenjingsuanzi` | `submit/tracks/shenjingsuanzi_agent/` | `TASKS/shenjingsuanzi/` |

## 状态与分数

| 文件 | 用途 |
|------|------|
| `STATUS/DAILY_STATUS.md` | **用户日更**（模式 + 分数） |
| `STATUS/SCOREBOARD.md` | 自动生成榜单 |
| `submit/track_pins.json` | 各赛道已发布 commit |
| `cundang/<track>/best.json` | 仓库内最高分元数据 |

## 归档（≈ 框架 ARCHIVE + SUBMISSIONS）

| 路径 | 含义 |
|------|------|
| `guidang/YYYYMMDDHHMM/<track>/` | 每次出分快照（含 `score_meta.json`） |
| `cundang/<track>/` | 历史最高分代码 |
| `SUBMISSIONS/README.md` | 逻辑别名说明 → 指向 guidang |

## 工具脚本

| 脚本 | 用途 |
|------|------|
| `scripts/archive_competition.py` | guidang + cundang + EXPERIMENTS |
| `scripts/generate_scoreboard.py` | 刷新 SCOREBOARD |
| `scripts/daily_sync.ps1` | 日更同步 |
| `submit/publish_track.ps1` | 单赛道 ACR 发布 |

## Cursor 规则

- `.cursor/rules/competition-workflow.mdc` — AI 标准流程
- `.cursor/rules/version-recovery.mdc` — 分赛道 pin
- `.cursor/rules/score-archive.mdc` — 归档规则

## 备份

- 框架迁移前快照：`BeforeGPT/<timestamp>/`
