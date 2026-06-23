# Shenjingsuanzi Agent Code

This legacy README is kept for `/app/submit/agent_code/README.md`. The final
review README copied to `/app/agent_code/README.md` is
`README.shenjingsuanzi.md`.

## Audit-safe Runtime

- Entrypoint: `/app/run.sh` with `FUSAI_TRACK=shenjingsuanzi`.
- Output: `/saisresult/submission.zip`.
- Required members:
  - `KS_pred_A.hdf5`
  - `cylinder_pred_A.hdf5`
  - `KS_pred_B.hdf5`
  - `cylinder_pred_B.hdf5`

The audit-safe image does not package or run KS training code. It generates KS
outputs from mounted test initial conditions with an IC-preserving baseline and
uses mounted cylinder inference scripts when available.

No training datasets, validation datasets, model checkpoints, or precomputed
prediction files should be baked into the final image.
