# 项目最高规则（比赛期间原则上不修改）

## 定位

本仓库为 **AI4S 智能体 CNS 挑战赛** 四赛道统一 monorepo（danbaizhi / drugclip / baxiangfenzi / shenjingsuanzi）。

## 不可违反

1. **赛题隔离**：各赛道独立开发、独立镜像、独立 pin、独立归档；禁止跨赛道 import 业务代码。
2. **只读 documen/**：赛题原始数据与 baseline 不得擅自修改。
3. **禁止自动消耗提交次数**：AI 不得未经用户确认向天池提交。
4. **禁止自动覆盖 best**：`cundang/<track>/` 仅当新分更高时替换；禁止手工删改 `best.json` 逻辑。
5. **禁止修改 GOVERNANCE/**（除非用户明确要求框架升级）。
6. **密钥不入库**：`submit/aliyun.env`、`submit/registry.env` 不得 commit。

## 版本与发布

- 单赛道发布：`.\submit\publish_track.ps1 -Track <name>`
- 禁止无 `-Tracks` 调用 `trigger_acr_build.ps1`
- 每赛道 pin 见 `submit/track_pins.json`

## 归档

- 每次出分：`py -3 scripts/archive_competition.py ... --git-commit <sha>`
- 时间线：`guidang/YYYYMMDDHHMM/<track>/`
- 最高分：`cundang/<track>/`
- **不再新建 `daima/`**（历史目录只读；新归档统一走 guidang）

## AI 入口

收到「开始执行」时，按顺序读取：

1. `GOVERNANCE/PROJECT_RULES.md`（本文件）
2. `GOVERNANCE/MODES.md`
3. `INDEX/PROJECT_INDEX.md`
4. `STATUS/DAILY_STATUS.md`
5. 对应 `TASKS/<track>/` 下四文件

对话结尾格式见 `.cursor/rules/competition-workflow.mdc`（四赛道总览 + 按需「需你操作」）。
