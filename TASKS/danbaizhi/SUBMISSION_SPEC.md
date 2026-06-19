# danbaizhi — 提交规范

## Docker

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `danbaizhi` |
| Dockerfile | `submit/Dockerfile.danbaizhi` |
| 镜像 | `crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/danbaizhi:0.1` |
| 输出 | `/saisresult/submission.zip` |

## zip 内容

- `1_conf1_pred.cif` … `1_conf4_pred.cif`
- `2_conf1_pred.cif` … `2_conf4_pred.cif`
- `3_conf1_pred.cif` … `3_conf3_pred.cif`
- `agent.log`（五阶段审计，缺失可取消成绩）

约束：≤100MB；全原子；无 NaN/Inf。

## 本地验证

```powershell
pip install -r Project/code/requirements.txt
cd Project
python code/main.py
python code/main.py verify-repro

py -3 submit/main.py --track danbaizhi --saisdata documen/Danbaizhi --saisresult submit/_local_saisresult --work-dir H:\Fusai
py -3 VALIDATION/check_submission.py --track danbaizhi --zip submit/danbaizhi/submission.zip
```

## Docker 本地

见原 `readme.md` 内容 → [`submit/DANBAIZHI_SUBMIT.md`](../../submit/DANBAIZHI_SUBMIT.md)

## 发布

```powershell
.\submit\publish_track.ps1 -Track danbaizhi
```

## 代码位置

- `Project/code/` — 主逻辑
- `Project/agent/` — prompt / config
- `submit/tracks/danbaizhi.py` — runner
