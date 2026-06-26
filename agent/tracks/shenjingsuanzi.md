# 任务 4 — Shenjingsuanzi（神经算子 PDE）

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `shenjingsuanzi` |
| 输出 | `/saisresult/submission.zip`（**4 个 HDF5**：A/B × KS/cylinder） |
| 输入 | `/saisdata/49/`、`/saisdata/48/`、`/saisdata/66/`（B榜） |
| 镜像 | `.../ai4s-lee/shenjingsuanzi:<tag>` |
| 环境 | V100 16G，6h；镜像 <5G |

## 实现

- `submit/tracks/shenjingsuanzi_agent/` — KS FNO1d 训练一次、A/B 双榜推理；cylinder 挂载 FNO
- 详细规范：`documen/Shenjingsuanzi/readme.md` §复赛评测提交规范
- 任务文档：`TASKS/shenjingsuanzi/`

## 环境变量

- `SHENJING_KS_PRESET=ks-q1`（默认）
- `SHENJING_KS_EPOCHS=28`
- `SHENJING_MODEL=fno`

## 本地验证

```powershell
pytest submit/tests/test_track_runners.py -k shenjingsuanzi
```
