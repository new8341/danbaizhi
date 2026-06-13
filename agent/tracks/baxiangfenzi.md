# 任务 2 — Baxiangfenzi（靶向分子 + 逆合成）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `baxiangfenzi` |
| 输出 | `/saisresult/result.zip`（`result1/2/3.csv`） |
| 输入 | `/saisdata/37/target1.pdb`, `target2.pdb`, `target3.pdb` |
| 镜像仓库 | `.../ai4s-lee/baxiangfenzi:<tag>` |

## 当前状态

- Runner：`submit/tracks/baxiangfenzi.py`（格式 baseline）  
- 待接入：分子生成 + 逆合成 Agent（禁止镜像内预置分子库）  

## 业务代码（规划）

建议目录：`Baxiangfenzi/code/`

## 本地验证

```powershell
py -3 submit/main.py --track baxiangfenzi --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir H:\Fusai
```
