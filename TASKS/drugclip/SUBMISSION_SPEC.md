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

## 代码

- `submit/tracks/drugclip.py`
- `submit/tracks/drugclip_agent/`（hybrid_max_qed + 两阶段 scoring）

## 发布

```powershell
.\submit\publish_track.ps1 -Track drugclip
```
