# 四赛道共享约定

## Docker 提交

| 项 | 约定 |
|----|------|
| 入口 | `/app/run.sh` → `submit/main.py` |
| 赛道选择 | 构建镜像时 `ENV FUSAI_TRACK=<track>`（每赛道独立镜像） |
| 输入 | `/saisdata`（DrugClip 例外：benchmark 在 `/app/benchmark`） |
| 输出 | `/saisresult/<output_name>`；先在 `/app` 打包再 `mv` |
| 错误 | JSON：`success` + `error.code` + `error.message` + `error.requestId` |

## 日志（agent.log / result.log）

每条赛道提交 zip 内须含日志，建议包含：

1. **Stage 1 — 理解**：读了哪些赛题文件/配置  
2. **Stage 2 — 假设**：本轮优化或策略选择  
3. **Stage 3 — 执行**：运行的命令、关键参数、耗时  
4. **Stage 4 — 验证**：本地检查或指标（若有）  
5. **Stage 5 — 产出**：输出文件列表与校验摘要  

任务 3 的 `Project/checkpoint/golden/agent.log` 为可参考范例。

## 归档

### 仓库内（四赛道 submit）

| 目录 | 策略 | 说明 |
|------|------|------|
| `guidang/YYYYMMDDHHMM/<track>/` | 按时间追加 | 每次出分都归档，不删旧记录 |
| `cundang/<track>/` | 固定目录，更高分替换 | 仅保留该赛道历史最高分代码 |

命令：`py -3 scripts/archive_competition.py --stamp ... --track ... --score ... --git-commit ...`  
详见 `guidang/README.md`、`cundang/README.md`、`.cursor/rules/score-archive.mdc`。

### 单赛道 daima（历史）

- 可能改变提交几何或分数的运行 → `daima/YYYYMMDDHHMM/`（启动时刻命名）  
- 含：相关代码快照 + 提交 zip + 评测 json（若有）  
- `documen/` **不得**写入归档副本以外的修改  

## ACR 镜像命名

```
<REGISTRY>/<NAMESPACE>/<track>:<TAG>
```

默认（见 `submit/registry.env.example`）：

- `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1`
- `.../drugclip:0.1`
- `.../baxiangfenzi:0.1`
- `.../shenjingsuanzi:0.1`

一键构建：`py -3 submit/build_all.py` 或 `.\submit\build_all.ps1`
