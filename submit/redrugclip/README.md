# Vendored ReDrugClip (hybrid_max_qed champion)

Champion DrugClip agent code vendored from `ReDrugClip/` for ACR cloud build
(GitHub clone does not include the sibling `ReDrugClip/` folder).

Synced paths: `src/`, `agent/`, `configs/`, `scripts/`.

Docker copies these to `/app/ReDrugClip/`; `submit/tracks/drugclip.py` runs
`scripts/run_agent.py --fast --strategy hybrid_max_qed`.
