# 任务 2 — Baxiangfenzi（靶向分子 + 逆合成）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `baxiangfenzi` |
| 输出 | `/saisresult/result.zip`（`result1/2/3.csv`） |
| 输入 | `/saisdata/37/target1.pdb`, `target2.pdb`, `target3.pdb` |
| 镜像仓库 | `.../ai4s-lee/baxiangfenzi:<tag>` |

## 当前状态

- Runner：`submit/tracks/baxiangfenzi.py` + `submit/tracks/baxiangfenzi_agent/`
- 流程：靶点分析 → RDKit 反应枚举候选 → AutoDock Vina 对接 → BRICS 逆合成路线

## 本地验证

```powershell
py -3 submit/main.py --track baxiangfenzi --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir H:\Fusai
```
