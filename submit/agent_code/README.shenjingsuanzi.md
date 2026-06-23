# Shenjingsuanzi Agent Code README

## Overall approach

This image runs the neural-operator PDE agent from `/app/run.sh`. The entrypoint
dispatches to `submit.tracks.shenjingsuanzi.ShenjingsuanziRunner`, which creates
four HDF5 predictions and packages them into the required zip file.

## Runtime data and output

- Input: mounted competition data under `/saisdata`.
- Output: `/saisresult/submission.zip`.
- Required zip members:
  - `KS_pred_A.hdf5`
  - `cylinder_pred_A.hdf5`
  - `KS_pred_B.hdf5`
  - `cylinder_pred_B.hdf5`

Each HDF5 file must contain a `tensor` dataset with the expected shape. The
first 20 steps must pass the IC consistency check with maximum absolute error
not greater than `5e-3`.

## Code layout in image

- `/app/run.sh`: unique evaluation entrypoint.
- `/app/submit/`: runner, packer, and track dispatch code.
- `/app/submit/tracks/shenjingsuanzi_agent/`: PDE prediction agent.
- `/app/agent/`: shared agent conventions and audit notes.
- `/app/agent_code/`: audit copy of inference code and this README.

## Model and prediction workflow

The audit-safe agent does not package or run KS training code. KS predictions
are generated from the mounted test initial-condition tensor with an
IC-preserving baseline. Cylinder predictions use the mounted inference script
when available. It logs selected data paths, source decisions, and generated
file names.

## Data and compliance

The final image should not contain training datasets, validation datasets,
model parameter files prohibited by the rules, or precomputed predictions.
Generic PDE method notes are allowed, but target-specific hyperparameter
instructions or fixed prediction assets are not.

## Environment

- Base image: PyTorch CUDA runtime.
- Python packages: `h5py`, `tqdm`, `matplotlib`.
- GPU runtime is expected for the normal path.

## Reproduction

Inside the image:

```bash
FUSAI_TRACK=shenjingsuanzi SAISDATA=/saisdata SAISRESULT=/saisresult sh /app/run.sh
```

Expected artifact:

```text
/saisresult/submission.zip
```

## External services and API keys

Current default pipeline does not require an LLM service. If an LLM-assisted
variant is enabled, configure:

- `LLM_API_KEY`: API key location.
- `LLM_BASE_URL`: provider base URL.
- `LLM_PROVIDER`: provider name.

Do not hard-code personal secrets in source code.
