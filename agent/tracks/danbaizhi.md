# 任务 3 — Danbaizhi（蛋白质构象系综）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `danbaizhi` |
| 输出 | `/saisresult/submission.zip`（mmCIF + `agent.log`） |
| 输入 | `/saisdata/1.json`, `2.json`, `3.json` |
| 镜像仓库 | `.../ai4s-lee/danbaizhi:<tag>` |

## 实现位置（已可用）

- 业务代码：`Project/code/`（入口 `main.py` → `generate_submission.py`）  
- Agent 文档：`Project/agent/config.md`, `prompt.md`, `log.md`  
- 线上参考分：**0.717129**（`Project/checkpoint/golden/`）  

## 本地验证

```powershell
py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir H:\Fusai
```

## 天池提交

镜像路径：  
`crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1`

**逐步说明**：[`submit/DANBAIZHI_SUBMIT.md`](../../submit/DANBAIZHI_SUBMIT.md)  
**本地 submission.zip**：[`submit/danbaizhi/submission.zip`](../../submit/danbaizhi/submission.zip)
