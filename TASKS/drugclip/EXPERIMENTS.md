# drugclip — 实验记录

| 时间戳 | 分数 | commit | 假设/备注 | 结果 |
|--------|------|--------|-----------|------|
| 202606191401 | 19.229531 | bb37aa2 | hybrid_max_qed_v2 天池 2026-06-19 14:01:53 追平冠军 | guidang only (below cundang best) |
| 202606170550 | 18.82 | 59c7bbf | native hybrid_max_qed + 两阶段 HybridScorer | 当前 guidang 最近 |
| 202606160708 | 0.0 | — | RDKit 简化 agent | **失败** |
| 202605252202 | 19.229531 | 203ab1a | ReDrugClip hybrid（初赛后） | cundang best（冠军参考） |

## 下一步

- [x] Sprint2 神经 DrugCLIP：LMDB + retrieval + `neural_hybrid` 策略（pin 待 publish）
- [ ] 平台验证神经路径 EF1%；若 LMDB 超时则调 `DRUGCLIP_LMDB_WORKERS`
- [ ] Sprint3：10-conformer + RRF 纯神经 rerank
