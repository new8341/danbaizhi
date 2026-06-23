# drugclip — 提交规范（复赛 2026-06）

## Docker

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `drugclip` |
| Dockerfile | `submit/Dockerfile.drugclip` |
| 镜像 | `.../ai4s-lee/drugclip:0.1` |
| 入口 | `/app/run.sh` |
| 输出 | `/saisresult/result.zip` → `result.csv` + `result.log` |
| 代码审核 | `/app/agent_code/README.md` |

## 测试集

- `benchmark/` 打包在镜像 `/app/benchmark/`（**仅输入，无标签**）
- `DRUGCLIP_BENCHMARK_ROOT=/app/benchmark`

## Agent 要求

- 自主完成：读数据 → 策略决策 → 推理/排序 → 打包
- `result.log` 须有可核验的 Agent 阶段记录
- 干净容器无人工干预可稳定跑通

## API Key

推理代码或环境变量须含可用 Key（出分后可停用）：

- `DRUGCLIP_LLM_API_KEY`
- `DRUGCLIP_LLM_BASE_URL`

## 禁止（成绩可置零）

| 禁止项 |
|--------|
| 预置 `result.csv` / `result.zip` / 候选答案表 |
| 复制/扰动预置结果 |
| 硬编码 task_id、ligand_id、标签 |
| 携带 DUD-E/LIT-PCBA active/inactive 或等价标签 |
| 本地 oracle 评测器 + 反馈调参 |
| 从 ChEMBL 等反向构建测试答案库 |
| 伪造/删减 `result.log` |

## README 必含（见 `/app/agent_code/README.md`）

方案与工作流、模型思路、数据来源与去泄漏、训练/推理流程、依赖版本、复现步骤、运行资源、API 配置、随机种子

## Docker 默认

`DRUGCLIP_STRATEGY=auto` → 有神经栈时 `neural_hybrid`，否则 `hybrid_max_qed_v2`（ACR slim 默认后者）

## 本地验证

```powershell
$env:DRUGCLIP_BENCHMARK_ROOT="submit/tests/fixtures/drugclip_mini"
$env:DRUGCLIP_MAX_TASKS="1"
py -3 submit/main.py --track drugclip --saisdata documen/DrugClip --saisresult submit/_local_saisresult --work-dir H:\Fusai
pytest submit/tests/test_track_runners.py -k drugclip
```

## 发布

```powershell
.\submit\publish_track.ps1 -Track drugclip
```

## 代码

`submit/tracks/drugclip_agent/`
