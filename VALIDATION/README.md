# 校验层 (VALIDATION)

发布或归档前建议运行：

```powershell
pytest submit/tests/
py -3 VALIDATION/check_structure.py
py -3 VALIDATION/check_submission.py --track danbaizhi --zip submit/danbaizhi/submission.zip
```

## 脚本

| 脚本 | 作用 |
|------|------|
| `check_structure.py` | GOVERNANCE / INDEX / STATUS / TASKS 是否齐全 |
| `check_submission.py` | 本地 zip 文件名与必要字段 |

## 与 pytest 分工

- **pytest**：runner 逻辑、registry、迷你 fixture
- **VALIDATION**：竞赛契约与文档框架完整性
