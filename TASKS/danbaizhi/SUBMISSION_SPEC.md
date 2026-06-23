# danbaizhi — 提交规范（复赛 2026-06）

## Docker

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `danbaizhi` |
| Dockerfile | `submit/Dockerfile.danbaizhi` |
| 镜像 | `.../ai4s-lee/danbaizhi:0.1` |
| 入口 | `/app/run.sh` |
| 输出 | `/saisresult/submission.zip` |
| 代码审核 | `/app/agent_code/README.md` |

## zip 内容

- `1_conf1_pred.cif` … `1_conf4_pred.cif`
- `2_conf1_pred.cif` … `2_conf4_pred.cif`
- `3_conf1_pred.cif` … `3_conf3_pred.cif`
- `agent.log`（五阶段审计，缺失可取消成绩）

约束：≤100MB；全原子；无 NaN/Inf。

## 选手须确保

- 推理在容器内由 Agent **实时生成**
- 不依赖镜像外文件；路径符合复赛评测规范
- 不从镜像内固定构象库筛选/抽取
- 不得硬编码测试集信息
- **API Key** 在代码或环境变量中（出分后可停用）

## README 必含（见 `/app/agent_code/README.md`）

方案介绍、模型思路、数据处理、环境依赖、复现步骤、API Key 与 base_url

## 镜像目录

```
/app/Project/         主业务（code/ + agent/）
/app/submit/          Docker runner
/app/agent_code/      审核 README + 代码副本
/app/run.sh           评测入口
```

## 本地验证

```powershell
pip install -r Project/code/requirements.txt
py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir H:\Fusai
py -3 VALIDATION/check_submission.py --track danbaizhi --zip submit/_local_saisresult/submission.zip
```

## 发布

```powershell
.\submit\publish_track.ps1 -Track danbaizhi
```

## 代码位置

- `Project/code/` — 预测主逻辑
- `Project/agent/` — Agent 配置
- `submit/tracks/danbaizhi.py` — runner（输出 `submission.zip`）

## B 榜 / 资格

不符合镜像要求或 B 榜无法正常出分 → 取消复赛资格
