# shenjingsuanzi — 经验教训

1. **KS ~1 分 ≠ 一定没训练**：2026-06-20 平台 log 显示 `KS_train exists=True`、`ks_train_done seconds=19266.8`（≈5.35h）、`windows=72000` — 训练已跑完，但 **A/B 榜仍仅 ~1 分** → 瓶颈是 **380 步自回归预报质量**，不是 baseline 兜底。
2. **6h 预算**：KS `ks-q1` 28 epoch 单题耗 ~5.3h，几乎挤占全部时限；cylinder 仍靠挂载 FNO（~40 分/榜）。
3. **cylinder A/B 分数相同量级**（39.70 / 40.01）且与历史完全一致 → 挂载 `run_inference.py` + `fno` checkpoint 路径饱和。
4. **挂载路径**：`/saisdata/49/problem1/data/KS_train.hdf5` 复赛可用；B 榜在 `/saisdata/66/`。
5. **cundang 57.69** 来自 `shenjingsuanzi/pdeburgers/` 参考路径，非当前 native agent 默认可达水平。
6. **下轮 P0**：缩短 KS 训练占时 + 强化长时 rollout 对齐（对照 pdeburgers）；P1 容器内 cylinder finetune。
