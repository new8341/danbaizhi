# baxiangfenzi — 提交规范

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `baxiangfenzi` |
| Dockerfile | `submit/Dockerfile.baxiangfenzi` |
| 镜像 | `.../ai4s-lee/baxiangfenzi:0.1` |
| 输出 | `/saisresult/result.zip` |

## Docker 默认预算

`MAX_CANDIDATES=200`, `MAX_DOCK=60`, `SELECT_POOL=15`

## 本地验证

```powershell
py -3 submit/main.py --track baxiangfenzi --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir H:\Fusai
pytest submit/tests/test_track_runners.py -k baxiangfenzi
```

## 代码

`submit/tracks/baxiangfenzi_agent/`（pocket box、Vina cache、BRICS 逆合成）

## 发布

```powershell
.\submit\publish_track.ps1 -Track baxiangfenzi
```
