# Fusai 共享 Agent 层

四赛道共用**编排约定与审计规范**；各赛道**核心算法**在对应目录实现。

## 与统一框架的对应

| 框架 | 本仓库 |
|------|--------|
| COMMON | `agent/shared/` + `scripts/` + `submit/` |
| TASKS/*/CODE | 见 `INDEX/PROJECT_INDEX.md` |
| GOVERNANCE | `GOVERNANCE/` |
| Agent 约定 | 本目录 `shared/` + `tracks/` |

## 目录

| 路径 | 作用 |
|------|------|
| `agent/shared/conventions.md` | 日志、错误码、归档、Docker 入口 |
| `agent/shared/pipeline.md` | 四阶段 Agent 闭环 |
| `agent/tracks/*.md` | 赛道快捷说明（详细见 `TASKS/<track>/`） |

## 与代码的对应

| 赛道 | 提交 runner | 业务实现 |
|------|-------------|----------|
| danbaizhi | `submit/tracks/danbaizhi.py` | `Project/code/` + `Project/agent/` |
| drugclip | `submit/tracks/drugclip.py` | `submit/tracks/drugclip_agent/` |
| baxiangfenzi | `submit/tracks/baxiangfenzi.py` | `submit/tracks/baxiangfenzi_agent/` |
| shenjingsuanzi | `submit/tracks/shenjingsuanzi.py` | `submit/tracks/shenjingsuanzi_agent/` |

## Docker

构建时 `agent/` 复制到 `/app/agent/`。扩展赛道：更新 `TASKS/<name>/` + `submit/tracks/<name>.py`，归档走 `scripts/archive_competition.py`（非 `daima/`）。
