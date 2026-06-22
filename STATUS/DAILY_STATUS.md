# 每日状态

> **用户每日仅维护本文件**，然后向 AI 输入「开始执行」。  
> AI 自主推进其余工作；**仅 blocked 时**在对话末尾提示「需你操作」（见 `competition-workflow.mdc`）。

```yaml
date: 2026-06-20
current_mode: OPTIMIZE

tracks:
  danbaizhi:
    mode: AUTO_ASSISTED
    best_cundang: 0.717129
    latest: 0.717129
    submissions_per_day: 2
    note: P1 3m 已完成(pLDDT92)；重启中断 P2(model2)；已续跑 P2+P3

  drugclip:
    mode: OPTIMIZE
    best_cundang: 19.229531
    latest: 19.229531
    submissions_per_day: 2
    note: 神经镜像已 publish(35ebe28)；build 内 git clone DrugCLIP

  baxiangfenzi:
    mode: OPTIMIZE
    best_cundang: 0.669636
    latest: 0.669304
    latest_time: "2026-06-20 13:30:49"
    submissions_per_day: 2
    note: Sprint1 restore≈Sprint2；未破 cundang

  shenjingsuanzi:
    mode: OPTIMIZE
    best_cundang: 81.777867
    latest: 81.777867
    latest_time: "2026-06-20 13:27:11"
    latest_detail: "KS_A=1.03 cyl_A=39.70 KS_B=1.04 cyl_B=40.01"
    submissions_per_day: 1
    note: B榜补齐+39分；KS仍baseline级，下轮KS真训练
```
