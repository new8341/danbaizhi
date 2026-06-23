# drugclip — 经验教训

## 要点

1. **0 分 → 18.82**：需完整 hybrid 打分链，非 RDKit 占位。
2. **两阶段评分**：fingerprint 分 + hybrid bonus 须与 ReDrugClip 一致。
3. **cundang 冠军 19.23** 来自 vendored ReDrugClip；native agent 仍差 ~0.4 EF。
4. benchmark 在镜像内，本地用 `DRUGCLIP_BENCHMARK_ROOT` 指到 fixture。

## 避免

- 一次改训练+推理+融合（应单假设）
- 未跑 pytest mini 就 publish
- drugclip ACR 个人版拉不动 3.4GB PyTorch（含 shenjingsuanzi base）；云端用 slim + hybrid_max_qed_v2（19.23）
