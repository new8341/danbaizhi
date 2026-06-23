# danbaizhi 复赛提交规范

## 镜像入口与输出

| 项目 | 值 |
|---|---|
| FUSAI_TRACK | `danbaizhi` |
| Dockerfile | `Dockerfile` / `submit/Dockerfile.danbaizhi` |
| Codex 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-danbaizhi:0.1` |
| Cursor 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1` |
| 唯一入口 | `/app/run.sh` |
| 当前 runner 输出 | `/saisresult/submission.zip` |

当前 runner 会先调用 `Project/code/main.py predict` 生成项目内部 `Project/result/output.zip`，再将其中内容重新打包为评测入口读取的 `/saisresult/submission.zip`。

## 镜像内审核结构

复赛最终镜像需补充完整智能体推理代码说明文档和必要材料。当前 Dockerfile 补齐：

```text
/app/Code/
├── Project_code/
└── danbaizhi_runner.py

/app/Reference/
└── agent/

/app/agent_code/
└── README.md
```

主运行代码仍保留在 `/app/Project/` 和 `/app/submit/`，入口仍是 `/app/run.sh`。

## 镜像内容要求

选手需确保：

- 推理代码可按赛题要求启动并完成预测任务；
- 推理过程不依赖镜像外的选手私有文件；
- 推理代码能在平台评测环境中稳定运行；
- 输入输出路径满足复赛规范；
- 结果由 Agent 在容器内生成，不由镜像自带结果复制或移动产生；
- 结果不能从镜像自带候选库或固定答案库中筛选、抽取得到；
- 不得硬编码测试集信息或通过其他违规方式获得评测结果；
- 如使用外部服务，应在推理代码或环境变量中配置 API Key。

## README 最低要求

`/app/agent_code/README.md` 至少说明：

- 方案整体介绍；
- 模型结构与建模思路；
- 数据处理流程；
- 环境依赖；
- 模型复现步骤；
- API Key 的位置、LLM 供应商、`base_url` 位置。

当前默认 pipeline 不依赖 LLM；如启用外部服务，使用：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_PROVIDER`

不得把个人密钥硬编码进源码。

## 合规风险

- 不得把训练集、验证集、违规模型权重或预计算预测结果打进最终镜像；
- 不得包含过强的目标专用指导说明或固定结果；
- 若平台日志提示读取其他文件名，需立即按平台日志修正 `submit/tracks/danbaizhi.py` 的 `output_name` 并重新验证。

## 本地验证

```powershell
pip install -r Project/code/requirements.txt
cd Project
python code/main.py predict
python code/main.py verify-repro

cd ..
py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir .
```

当前 Codex 环境中 `py -3` 不可用时，需在本机 Python 环境或 ACR 构建日志中完成验证。
