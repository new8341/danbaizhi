# 每日状态

> **用户每日仅维护本文件**，然后向 AI 输入「开始执行」。

```yaml
date: 2026-06-19
current_mode: OPTIMIZE

tracks:
  danbaizhi:
    mode: AUTO_ASSISTED
    yesterday: 0.717129
    today: 0.717129
    leaderboard_1: 0.8104
    submissions_left: 2
    note: Sprint auto_prior max24 + P1 3m model_1/2；待 publish 提交

  drugclip:
    mode: LEADERBOARD
    yesterday: 19.229531
    today: 19.229531
    leaderboard_1: 48.5629
    submissions_left: 1
    note: 指纹天花板~19.23；保留今日1次，转神经 DrugCLIP Sprint2

  baxiangfenzi:
    mode: OPTIMIZE
    yesterday: 0.669636
    today: 0.669304
    leaderboard_1: 0.8875
    submissions_left: 1
    note: Sprint3 route_enum 已编码；待 publish 提交

  shenjingsuanzi:
    mode: OPTIMIZE
    yesterday: 42.09
    today: 42.090454
    leaderboard_1: 181.15
    leaderboard_detail: "KS_A=11.61 cyl_A=67.87 KS_B=32.48 cyl_B=69.17"
    submissions_left: 0
    note: 明日首提；KS fno1d_train + 四文件 A/B
```

## 今日待办（AI 可读）

- [ ] publish + 提交 **baxiangfenzi** Sprint3（1 次）
- [ ] publish + 提交 **danbaizhi** auto_prior P1 3m（1～2 次）
- [ ] **drugclip**：不提交，启动神经 MVP
- [ ] **shenjingsuanzi**：publish 备明日；grep log 确认 `ks_source=fno1d_train`
- [ ] 出分后归档 guidang

## 备注

复赛总成绩 = 最高两个赛道 z-score 之和（见 `documen/fusai.md`）。  
详细规划见 `STATUS/SUBMISSION_PLAN.md`。
