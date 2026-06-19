# shenjingsuanzi — 实验记录

| 时间戳 | 分数 | commit | 假设/备注 | 结果 |
|--------|------|--------|-----------|------|
| 202606170549 | 42.090454 | 1266385 | FNO1d agent Q1=2.39 Q2=39.70 | guidang 最近 |
| 202606160716 | 32.904013 | 65d41a9 | KS baseline | |
| 202605201228 | 57.685109 | 203ab1a | pdeburgers pipeline（初赛） | cundang best |

## 诊断

- Q1 ~2.39 偏低 → 疑 KS_train 未挂载或 λ₂ conditioning 弱
- 日志应含 `ks_source=fno1d_train`

## 下一步

- [ ] 确认评测挂载 `KS_train.hdf5`
- [ ] 增 epoch / 调 window bias / λ₂
