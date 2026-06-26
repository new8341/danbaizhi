# drugclip 复赛提交规范

## 镜像入口与输出

| 项目 | 值 |
|---|---|
| FUSAI_TRACK | `drugclip` |
| Dockerfile | `Dockerfile.drugclip` / `submit/Dockerfile.drugclip` |
| Codex 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-drugclip:0.1` |
| Cursor 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/drugclip:0.1` |
| 唯一入口 | `/app/run.sh` |
| 输出 | `/saisresult/result.zip` |

`result.zip` 至少应包含：

- `result.csv`
- `result.log`

## 测试集输入

主办方提供的 `benchmark.zip` 只包含测试输入，不包含 active/inactive 标签或标准答案。本赛道要求将该测试输入打包到镜像中；当前 Dockerfile 将 `documen/DrugClip/benchmark/` 复制到 `/app/benchmark/`。

## 镜像内容要求

镜像必须能够在无人工干预下完成：

1. 数据读取；
2. 策略选择；
3. 推理或排序；
4. 结果生成；
5. 打包输出。

镜像内补齐审核材料：

- `/app/agent_code/README.md`
- `/app/agent_code/drugclip_runner.py`
- `/app/agent_code/drugclip_agent/`
- `/app/agent_code/agent/`

## 禁止事项

- 不得预置 `result.csv`、`result.zip`、候选答案表或可还原最终排名的等价文件。
- 不得通过复制、移动、解压或轻微扰动预置结果生成提交。
- 不得硬编码 `task_id`、`ligand_id`、行顺序、已知标签或针对单个测试任务的答案规则。
- 不得携带或下载 DUD-E / LIT-PCBA 原始 active/inactive 文件、标签归档、完整原始数据集或等价镜像。
- 不得携带或调用可返回测试集 EF1% 的标签评测器。
- 不得访问 DUD-E、LIT-PCBA 官网或镜像站下载测试标签。
- 不得通过 Hugging Face、GitHub 等渠道获取等价标签。
- 不得按测试靶点从 ChEMBL 或其他数据库反向构建与测试 active 高度重合的参考库。
- 不得伪造、删减或隐藏关键 Agent 运行过程，或提交与实际运行不符的 `result.log`。

允许使用测试集之外的数据进行通用预训练或模型能力增强，但不得直接或间接恢复测试标签、构建答案库或利用线上反馈反复选择结果。

## API Key 与外部服务

规则要求如使用外部服务，应在推理代码或环境变量中包含可用 API Key。当前默认 pipeline 不依赖 LLM；如启用外部服务，使用以下环境变量：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_PROVIDER`

不得把个人密钥硬编码到源码或提交文档中。

## README 最低要求

`/app/agent_code/README.md` 至少说明：

- 方案整体介绍和 Agent 工作流程；
- 模型结构、建模思路和主要创新点；
- 数据来源、数据处理和去泄漏方法；
- 训练、微调、推理和排序流程；
- 完整环境依赖及版本；
- 完整复现步骤；
- 预期运行时间、GPU/CPU/内存/磁盘需求；
- 外部服务、模型、API Key 和 `base_url` 配置位置；
- 随机种子、非确定性来源和已知复现差异。

## 本地验证

```powershell
$env:DRUGCLIP_BENCHMARK_ROOT="submit/tests/fixtures/drugclip_mini"
$env:DRUGCLIP_MAX_TASKS="1"
py -3 submit/main.py --track drugclip --saisdata documen/DrugClip --saisresult submit/_local_saisresult --work-dir .
pytest submit/tests/test_track_runners.py -k drugclip
```

当前 Codex 环境中 `py -3` 不可用时，需在本机 Python 环境或 ACR 构建日志中完成验证。
