# shenjingsuanzi — 经验教训

1. **Q1/Q2 分项**：总分 42 但 Q1≈2 说明 KS 分支未真正训练或 fallback。
2. **挂载路径**：`/saisdata/48/KS_train.hdf5` 必须存在才走 `fno1d_train`。
3. **6h 预算**：KS epoch 与 problem2 inference 需权衡；`score-push` preset 偏 Q2。
4. **cundang 57.69** 来自 reference pdeburgers，非当前 native agent 路径。
5. cylinder 依赖挂载 `run_inference.py`；失败会 sample 兜底（低分）。
