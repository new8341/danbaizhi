# shenjingsuanzi — 实验记录

| 时间戳 | 分数 | commit | 假设/备注 | 结果 |
|--------|------|--------|-----------|------|
| 202606201327 | 81.777867 | 35ebe28 | KS_A=1.03 cyl_A=39.70 KS_B=1.04 cyl_B=40.01 天池 2026-06-20 13:27:11 | cundang replaced |
| 202606191402 | 42.090454 | 26d5745 | ks-q1 KS_train失败 ComplexHalf fallback Q1=2.39 Q2=39.70 | guidang only (below cundang best) |
| 202606170549 | 42.090454 | 1266385 | FNO1d agent Q1=2.39 Q2=39.70 | guidang 最近 |
| 202606160716 | 32.904013 | 65d41a9 | KS baseline | |
| 202605201228 | 57.685109 | 203ab1a | pdeburgers pipeline（初赛） | cundang best |

## 诊断

- Q1 ~2.39 偏低 → 疑 KS_train 未挂载或 λ₂ conditioning 弱
- 日志应含 `ks_source=fno1d_train`

## 下一步

- [ ] 确认评测挂载 `KS_train.hdf5`
- [ ] 增 epoch / 调 window bias / λ₂
