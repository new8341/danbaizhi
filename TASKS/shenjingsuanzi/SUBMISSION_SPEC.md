# shenjingsuanzi 复赛提交规范

## 镜像入口与输出

| 项目 | 值 |
|---|---|
| FUSAI_TRACK | `shenjingsuanzi` |
| Dockerfile | `Dockerfile.shenjingsuanzi` / `submit/Dockerfile.shenjingsuanzi` |
| Codex 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-shenjingsuanzi:0.1` |
| Cursor 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/shenjingsuanzi:0.1` |
| 唯一入口 | `/app/run.sh` |
| 输出 | `/saisresult/submission.zip` |
| Agent 代码审核 | `/app/agent_code/README.md` |

评测系统启动容器后，只调用 `/app/run.sh`。Agent 运行完成后读取 `/saisresult/submission.zip`。

## submission.zip 内容

`submission.zip` 必须包含四个文件：

| 文件 | 说明 |
|---|---|
| `KS_pred_A.hdf5` | 第一题 A 榜预测 |
| `cylinder_pred_A.hdf5` | 第二题 A 榜预测 |
| `KS_pred_B.hdf5` | 第一题 B 榜预测 |
| `cylinder_pred_B.hdf5` | 第二题 B 榜预测 |

以下情况对应题目得 0 分，不影响另一题：

- 缺少对应预测文件；
- HDF5 文件中不存在 `tensor` 字段；
- `tensor` shape 与标准不符，特别是 `N` 与测试集样本数不一致；
- IC 一致性检验未通过，前 20 步最大绝对误差大于 `5e-3`。

## 镜像内审核结构

当前 Dockerfile 已补齐：

```text
/app/agent_code/
├── README.md
├── shenjingsuanzi_agent/
└── agent/
```

主运行代码仍保留在 `/app/submit/`，入口仍是 `/app/run.sh`。

## 镜像内容规范

允许包含：

- Agent 运行环境；
- Agent 代码，放置于 `/app/` 相关目录；
- PDE 相关通用知识库、Skill、MCP 工具。

禁止包含：

- 训练代码及训练脚本；
- 训练集、验证集等任何形式的数据集；
- 模型参数文件；
- 预先计算好的预测结果文件；
- 针对性过强的指导说明，例如明确指定某题训练方法、具体超参数或固定调参路线。

通用方法经验可以保留，但不能包含目标专用答案或强针对性提示。

## 复赛代码提交入口

6 月 26 日 14:00 至 6 月 28 日 14:00，排行榜前 20 名需通过代码提交入口提交 Agent 方案说明，形式可为 Word、Markdown、PDF 或 PPT。未按时提交视为放弃晋级资格。

## 本地验证

```powershell
py -3 submit/main.py --track shenjingsuanzi --saisdata documen/Shenjingsuanzi --saisresult submit/_local_saisresult --work-dir .
```

提交前至少检查：

- `/saisresult/submission.zip` 存在；
- zip 内四个 HDF5 文件齐全；
- 每个 HDF5 有 `tensor` 字段；
- A/B 榜文件名完全匹配大小写；
- IC 前 20 步一致性满足误差要求。

当前 Codex 环境中 `py -3` 不可用时，需在本机 Python 环境或 ACR 构建日志中完成验证。
