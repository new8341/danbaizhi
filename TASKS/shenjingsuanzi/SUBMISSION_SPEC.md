# shenjingsuanzi — 提交规范

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `shenjingsuanzi` |
| Dockerfile | `submit/Dockerfile.shenjingsuanzi` |
| 镜像 | `.../ai4s-lee/shenjingsuanzi:0.1` |
| 输出 | `/saisresult/submission.zip` |

## 环境变量

- `SHENJING_KS_PRESET=score-push`（默认）
- `SHENJING_KS_EPOCHS=24`
- `SHENJING_MODEL=fno`（problem2）

## 本地验证

```powershell
pytest submit/tests/test_track_runners.py -k shenjingsuanzi
```

## 代码

`submit/tracks/shenjingsuanzi_agent/`（FNO1d KS + cylinder inference 挂载）

## 发布

```powershell
.\submit\publish_track.ps1 -Track shenjingsuanzi
```
