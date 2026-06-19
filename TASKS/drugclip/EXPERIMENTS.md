# drugclip — 实验记录

| 时间戳 | 分数 | commit | 假设/备注 | 结果 |
|--------|------|--------|-----------|------|
| 202606170550 | 18.82 | 59c7bbf | native hybrid_max_qed + 两阶段 HybridScorer | 当前 guidang 最近 |
| 202606160708 | 0.0 | — | RDKit 简化 agent | **失败** |
| 202605252202 | 19.229531 | 203ab1a | ReDrugClip hybrid（初赛后） | cundang best（冠军参考） |

## 下一步

- [ ] 对齐 ReDrugClip `_fingerprint_scores` + `_hybrid_bonuses` 细节（已部分完成）
- [ ] 评估 hybrid_max_qed_v2 或 champion 融合
