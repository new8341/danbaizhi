# baxiangfenzi — 提交规范（复赛 2026-06）

## Docker

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `baxiangfenzi` |
| Dockerfile | `submit/Dockerfile.baxiangfenzi` |
| 镜像 | `.../ai4s-lee/baxiangfenzi:0.1` |
| 入口 | `/app/run.sh` |
| 输出 | `/saisresult/result.zip` |

## 镜像目录（复赛要求）

```
/app/Code/
├── main.py              代码审核入口
├── README.md            方案/环境/API Key 说明
└── baxiangfenzi_agent/  业务实现
/app/Reference/          参考文献
/app/submit/             统一 runner
/app/run.sh              评测入口
```

## B 榜

- `/saisdata/37/target1.pdb`、`target2.pdb`、`target3.pdb` **路径与文件名不变**，内容替换
- 输出不得与 A 榜完全相同（视为硬编码作弊）

## 选手须确保

- 推理在容器内由 Agent **实时生成**，非复制/移动预置结果
- 不依赖镜像外文件、本地绝对路径、不可获取的外部资源
- 不从镜像内固定分子库筛选答案
- **API Key** 须在代码或环境变量中配置（出分后可停用）

## README 必含（见 `/app/Code/README.md`）

方案介绍、模型思路、数据处理、环境依赖、复现步骤、API Key 位置与 base_url

## Docker 默认预算

`BAXIANG_MAX_CANDIDATES=200`, `BAXIANG_MAX_DOCK=60`, `BAXIANG_SELECT_POOL=15`

## 本地验证

```powershell
py -3 submit/main.py --track baxiangfenzi --saisdata documen/Baxiangfenzi --saisresult submit/_local_saisresult --work-dir H:\Fusai
pytest submit/tests/test_track_runners.py -k baxiangfenzi
```

## 发布

```powershell
.\submit\publish_track.ps1 -Track baxiangfenzi
```

## 代码

`submit/tracks/baxiangfenzi_agent/` — Vina + BRICS 逆合成
