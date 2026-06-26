# baxiangfenzi 复赛提交规范

## 镜像入口与输出

| 项目 | 值 |
|---|---|
| FUSAI_TRACK | `baxiangfenzi` |
| Dockerfile | `Dockerfile.baxiangfenzi` / `submit/Dockerfile.baxiangfenzi` |
| Codex 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-baxiangfenzi:0.1` |
| Cursor 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/baxiangfenzi:0.1` |
| 唯一入口 | `/app/run.sh` |
| 输出 | `/saisresult/result.zip` |

`result.zip` 当前包含：

- `result1.csv`
- `result2.csv`
- `result3.csv`
- `result.log`

## 镜像内审核结构

复赛最终镜像需在 `/app/` 下提供完整推理代码说明文档和必要材料。当前 Dockerfile 补齐：

```text
/app/Code/
├── baxiangfenzi_runner.py
└── baxiangfenzi_agent/

/app/Reference/
└── agent/

/app/agent_code/
└── README.md
```

主运行代码仍保留在 `/app/submit/`，入口仍是 `/app/run.sh`。

## B 榜输入要求

B 榜会替换 `/saisdata/37/` 下的三个靶点文件，但路径和文件名保持不变：

- `/saisdata/37/target1.pdb`
- `/saisdata/37/target2.pdb`
- `/saisdata/37/target3.pdb`

推理代码必须每次读取挂载文件，不能依赖 A 榜靶点缓存或固定结果。若 B 榜结果与 A 榜完全相同，存在被判定为硬编码作弊的风险。

## 镜像内容要求

选手需确保：

- 推理代码可按赛题要求启动并完成预测任务；
- 推理过程不依赖镜像外的选手私有文件；
- 推理代码能在平台评测环境稳定运行；
- 输入输出路径满足复赛规范；
- 结果由 Agent 在容器内生成，不能由镜像自带结果复制/移动产生；
- 结果不能从镜像自带分子/合成路径列表库中筛选或抽取得到；
- 不得硬编码测试集信息或通过其他违规方式获取评测结果；
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

## 本地验证

```powershell
py -3 submit/main.py --track baxiangfenzi --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir .
pytest submit/tests/test_track_runners.py -k baxiangfenzi
```

当前 Codex 环境中 `py -3` 不可用时，需在本机 Python 环境或 ACR 构建日志中完成验证。
