# danbaizhi — 任务 3 蛋白质构象系综

[第四届世界科学智能大赛 — AI4S 智能体 CNS 挑战赛](https://github.com/new8341/danbaizhi) · 任务 3：蛋白质构象系综生成 Agent

线上参考分 **0.717129**（ColabFold MSA 先验 + 模板 hybrid 管线）。

## 仓库结构

| 路径 | 说明 |
|------|------|
| `Project/` | 预测与打包主代码（`code/main.py`） |
| `submit/` | Docker 提交（`/app/run.sh` → `/saisresult/submission.zip`） |
| `submit/danbaizhi/` | 本地已生成的 `submission.zip` 与 `manifest.json` |
| `agent/` | Agent 约定与各赛道说明 |
| `documen/Danbaizhi/` | 赛题输入 JSON 样例（只读） |

## 本地复现

```powershell
pip install -r Project/code/requirements.txt
cd Project
python code/main.py
python code/main.py verify-repro
```

## Docker 提交（天池）

完整步骤见 [`submit/DANBAIZHI_SUBMIT.md`](submit/DANBAIZHI_SUBMIT.md)。

```powershell
docker build -f submit/Dockerfile.danbaizhi `
  -t crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1 .

docker run --rm `
  -v ${PWD}/documen/Danbaizhi:/saisdata:ro `
  -v ${PWD}/submit/_local_saisresult:/saisresult `
  crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1
```

天池镜像地址：`crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1`

## 提交包格式

`/saisresult/submission.zip` 内含：

- `1_conf1_pred.cif` … `1_conf4_pred.cif`
- `2_conf1_pred.cif` … `2_conf4_pred.cif`
- `3_conf1_pred.cif` … `3_conf3_pred.cif`
- `agent.log`

## 许可与合规

- 赛题原始文件见 `documen/Danbaizhi/`，请勿将私有评测数据写入仓库。
- 勿提交 ACR 密码、`registry.env` 或 API Key。
