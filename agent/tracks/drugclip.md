# 任务 1 — DrugClip（虚拟筛选）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `drugclip` |
| 输出 | `/saisresult/result.zip`（`result.csv` + `result.log`） |
| 输入 | `/app/benchmark/`（镜像内，不挂载测试集） |
| 镜像仓库 | `.../ai4s-lee/drugclip:<tag>` |

## 当前状态

- Runner：`submit/tracks/drugclip.py`（格式 baseline，哈希占位 score）  
- 待接入：DrugCLIP 推理 + Agent 训练/排序优化  

## 业务代码（规划）

建议目录：`DrugClip/code/`（从 `documen/DrugClip` 只读引用数据，不改 documen）

## 本地验证（迷你集）

```powershell
$env:DRUGCLIP_BENCHMARK_ROOT="submit/tests/fixtures/drugclip_mini"
$env:DRUGCLIP_MAX_TASKS="1"
py -3 submit/main.py --track drugclip --saisdata documen/DrugClip --saisresult submit/_local_saisresult --work-dir H:\Fusai
```
