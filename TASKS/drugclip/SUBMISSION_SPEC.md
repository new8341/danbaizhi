# drugclip — 提交规范

| 项 | 值 |
|----|-----|
| FUSAI_TRACK | `drugclip` |
| Dockerfile | `submit/Dockerfile.drugclip` |
| 镜像 | `.../ai4s-lee/drugclip:0.1` |
| 输出 | `/saisresult/result.zip` |

## 本地验证

```powershell
$env:DRUGCLIP_BENCHMARK_ROOT="submit/tests/fixtures/drugclip_mini"
$env:DRUGCLIP_MAX_TASKS="1"
py -3 submit/main.py --track drugclip --saisdata documen/DrugClip --saisresult submit/_local_saisresult --work-dir H:\Fusai
pytest submit/tests/test_track_runners.py -k drugclip
```

## Docker 默认

`DRUGCLIP_STRATEGY=auto`（有权重+GPU 栈时 `neural_hybrid`，否则 `hybrid_max_qed_v2`）

| 变量 | 默认 | 说明 |
|------|------|------|
| `DRUGCLIP_NEURAL_BLEND` | 0.9 | 神经分与指纹分融合权重 |
| `DRUGCLIP_NUM_CONF` | 1 | 每分子构象数 |
| `DRUGCLIP_BATCH_SIZE` | 16 | 检索 batch |
| `DRUGCLIP_WEIGHTS_DIR` | `/app/weights` | dude + litpcba 权重 |

## 发布

```powershell
.\submit\publish_track.ps1 -Track drugclip
```
