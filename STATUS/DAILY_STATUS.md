# 每日状态

> **用户每日仅维护本文件**，然后向 AI 输入「开始执行」。

```yaml
date: 2026-06-17
current_mode: OPTIMIZE   # BOOTSTRAP | OPTIMIZE | LEADERBOARD | AUTO_ASSISTED

tracks:
  danbaizhi:
    mode: AUTO_ASSISTED
    yesterday: 0.717129
    today: 0.717129
    note: ColabFold A1 跑 problem_1 predictions_msa_3m（CPU）

  drugclip:
    mode: OPTIMIZE
    yesterday: 18.82
    today: 18.82
    note: Sprint hybrid_max_qed_v2 待 publish

  baxiangfenzi:
    mode: OPTIMIZE
    yesterday: 0.667
    today: 0.669636
    note: Sprint2 6:4+best_route 待 publish

  shenjingsuanzi:
    mode: OPTIMIZE
    yesterday: 42.09
    today: 42.09
    note: Sprint ks-q1 preset 待 publish

  danbaizhi:
    mode: AUTO_ASSISTED
    yesterday: 0.717129
    today: 0.717129
    note: auto_prior+ColabFold 3m 待 publish（权重跑完自动增益）
```

## 今日待办（AI 可读）

- [ ] 四赛道 Sprint 已 commit → 依次 publish_track.ps1
- [ ] baxiangfenzi：Sprint2 6:4+best_route 待天池验证
- [ ] drugclip：hybrid_max_qed_v2 待天池验证
- [ ] shenjingsuanzi：ks-q1 待天池验证
- [ ] danbaizhi：publish 后 ColabFold 3m 完成即自动多模型先验

## 备注

复赛总成绩 = 最高两个赛道 z-score 之和（见 `documen/fusai.md`）。
