# 运行模式

## 模式定义

| 模式 | 何时使用 | AI 行为 |
|------|----------|---------|
| **BOOTSTRAP** | 新赛道接入、镜像首次打通 | 读赛题 → 最小可提交 → pytest + validation |
| **OPTIMIZE** | 有 baseline 分，需涨分 | 读 EXPERIMENTS + LESSONS → 单假设小步改 → 本地测 → 建议发布 |
| **LEADERBOARD** | 已发布镜像、待平台出分 | 不重复大改；准备归档命令；分析日志 |
| **AUTO_ASSISTED** | 长跑任务（ColabFold 等） | 监控进度；完成后衔接下游脚本；不中断进程 |

## 当前默认（见 STATUS/DAILY_STATUS.md）

| 赛道 | 建议模式 |
|------|----------|
| danbaizhi | AUTO_ASSISTED（ColabFold A1 权重/预测） |
| drugclip | OPTIMIZE（距冠军 ~19.23 有 gap） |
| baxiangfenzi | LEADERBOARD（Sprint1 已发布） |
| shenjingsuanzi | OPTIMIZE（Q1 偏弱） |

## 切换规则

- 用户在 `STATUS/DAILY_STATUS.md` 设置 `current_mode`
- 分数连跌 2 次同策略 → 建议切 OPTIMIZE 并换假设
- 镜像已 publish 且未提交 → LEADERBOARD
- 外部依赖下载/训练 >2h → AUTO_ASSISTED

## 禁止

- 自动切换为「提交天池」
- 自动修改 `track_pins.json` 或 push tag（须用户确认 publish）
