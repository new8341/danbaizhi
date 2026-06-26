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
    note: P1 ColabFold model_3 进行中(recycle2 pLDDT92)；完成后 republish

  drugclip:
    mode: OPTIMIZE
    best_cundang: 19.229531
    latest: 19.229531
    submissions_per_day: 2
    note: 神经镜像已 publish(35ebe28)；build 内 git clone DrugCLIP

  baxiangfenzi:
    mode: OPTIMIZE
    best_cundang: 0.669636
    latest: 0.665760
    submissions_per_day: 2
    note: 已回滚 Sprint1(208eec8)并 publish

  shenjingsuanzi:
    mode: OPTIMIZE
    best_cundang: 57.685109
    latest: 42.090454
    submissions_per_day: 1
    note: KS fp32+路径增强已 publish(35ebe28)；待提交验证
```
