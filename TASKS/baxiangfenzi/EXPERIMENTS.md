# baxiangfenzi — 实验记录

| 时间戳 | 分数 | commit | 假设/备注 | 结果 |
|--------|------|--------|-----------|------|
| 202606172318 | 0.669636 | 208eec8 | Sprint1 天池出分 2026-06-17 23:18:33 | cundang replaced |
| 202606160717 | 0.666884 | 8c87d20 | RDKit+Vina baseline | cundang best |
| 20260617 | ~0.667 | 208eec8 | Sprint1：pocket box、官方权重、dock 排序 | 已 publish，待平台确认 |

## Sprint1 改动

- HETATM → CA density → COM 口袋盒
- 受体 PDBQT 缓存
- 对接池按结合相关性排序（非 SA）
- `score_route()` 逆合成分

## Sprint2（进行中）

- 假设：复赛评分 **6:4**（分子:路线），Sprint1 误用 7:3 选分子
- 改动：`official_composite(0.6/0.4)`、`best_route_for_target()`、`SELECT_POOL=25`
- 状态：**待 publish**

## drugclip Sprint（待 publish）

- hybrid_max_qed_v2：qed 0.04 + smiles_sim 0.08 + LIT-PCBA 多参考

## shenjingsuanzi Sprint（待 publish）

- ks-q1 preset：28 epoch、宽 window pin、KS_train 多路径挂载

## danbaizhi Sprint（待 publish）

- predict 时 `DANBAIZHI_AUTO_PRIOR=1` 扫描 colabfold（含 predictions_msa_3m）
