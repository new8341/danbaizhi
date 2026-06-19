# 开发规则

## 代码布局

| 层 | 路径 | 职责 |
|----|------|------|
| 提交 runner | `submit/tracks/<track>.py` | saisdata → zip → saisresult |
| 业务 Agent | `submit/tracks/<track>_agent/` 或 `Project/` | 科学逻辑 |
| 约定 | `agent/shared/` | 日志五阶段、Docker 契约 |
| 文档 | `TASKS/<track>/` | 需求、实验、教训 |

## 分支策略（本项目）

- **不采用** `task*-dev` / `task*-best` 多分支（见框架包 D 已否决）
- `main` = 开发线；`cundang/` + `track_pins.json` = 各赛道 best 快照
- 回滚：`.\submit\restore_track.ps1 -Track <name> -Node <commit>`

## 改动原则

1. **单假设单 commit**：一次只验证一个优化点
2. **共享层改动**须跑 `pytest submit/tests/` + `py -3 VALIDATION/check_structure.py`
3. **发布前**建议跑 `VALIDATION/check_submission.py`（若有本地 zip）
4. agent.log 须含五阶段（理解→假设→执行→验证→产出）

## 实验记录

- 出分后 `archive_competition.py` 自动追加 `TASKS/<track>/EXPERIMENTS.md`
- 禁止重复已标记为 failed 的实验（先读 EXPERIMENTS）

## 长期任务

- ColabFold：`Project/scripts/start_danbaizhi_a1.ps1`
- 不 kill WSL 内 `colabfold_batch` 除非用户要求
