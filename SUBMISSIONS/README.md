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

## 复赛 Agent 方案说明（代码提交 6/26–6/28）

完整 Markdown 源稿：**[`agent_proposals/`](agent_proposals/)**

| 赛道 | 方案文档 |
|------|----------|
| shenjingsuanzi | [agent_proposals/shenjingsuanzi.md](agent_proposals/shenjingsuanzi.md) |
| baxiangfenzi | [agent_proposals/baxiangfenzi.md](agent_proposals/baxiangfenzi.md) |
| drugclip | [agent_proposals/drugclip.md](agent_proposals/drugclip.md) |
| danbaizhi | [agent_proposals/danbaizhi.md](agent_proposals/danbaizhi.md) |

可导出为 PDF/Word 后上传天池「代码提交」入口。

**LLM API Key 安全注入**（ACR 构建参数，勿写入 Git）：[`submit/LLM_API_KEY_ACR.md`](../submit/LLM_API_KEY_ACR.md)

## 复赛 Docker 规范对照

各赛道详细规则见 `TASKS/<track>/SUBMISSION_SPEC.md`：

| 赛道 | 输出 | 代码审核目录 |
|------|------|-------------|
| shenjingsuanzi | `submission.zip`（4×HDF5 A+B） | `/app/agent_code/` |
| baxiangfenzi | `result.zip` | `/app/Code/` + `/app/Reference/` |
| drugclip | `result.zip` | `/app/agent_code/` |
| danbaizhi | `submission.zip` | `/app/agent_code/` |

- `submit/danbaizhi/submission.zip`
- `submit/danbaizhi/manifest.json`
