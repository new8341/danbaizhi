# Fusai 共享 Agent 层

四赛道共用**编排约定与审计规范**；各赛道**核心算法与工具**在对应目录实现。

## 目录

| 路径 | 作用 |
|------|------|
| `agent/shared/conventions.md` | 日志、错误码、归档、Docker 入口等统一约定 |
| `agent/shared/pipeline.md` | 大赛四阶段 Agent 闭环（理解→假设→演进→验证） |
| `agent/tracks/*.md` | 各赛道入口说明、数据路径、实现位置 |

## 与代码的对应关系

| 赛道 | 提交 runner | 业务实现（当前） |
|------|-------------|------------------|
| danbaizhi | `submit/tracks/danbaizhi.py` | `Project/code/` + `Project/agent/` |
| drugclip | `submit/tracks/drugclip.py` | 待接入 `DrugClip/`（规划） |
| baxiangfenzi | `submit/tracks/baxiangfenzi.py` | 待接入（规划） |
| shenjingsuanzi | `submit/tracks/shenjingsuanzi.py` | 挂载 `/saisdata/49` baseline 推理 |

## Docker 中的位置

构建镜像时 `agent/` 会复制到容器 **`/app/agent/`**，便于最后一周代码审核与 README 说明（PDE 赛道还要求 `/app/agent_code/`，可在该赛道 Dockerfile 中额外 COPY 业务代码）。

## 扩展方式

1. 在 `agent/tracks/<name>.md` 记录赛道约束与命令。
2. 在 `submit/tracks/<name>.py` 的 `run()` 中调用该赛道 Agent 入口（子进程或 Python import）。
3. 跑模型后按 `readme.md` 归档到 `daima/YYYYMMDDHHMM/`。
