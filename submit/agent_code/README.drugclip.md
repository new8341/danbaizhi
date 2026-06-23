# DrugClip Agent Code README

## Overall approach

This image runs the DrugClip virtual-screening agent from `/app/run.sh`.
The entrypoint dispatches to `submit.tracks.drugclip.DrugclipRunner`, which
loads the packaged benchmark input, scores ligands, writes `result.csv`, and
records the autonomous process in `result.log`.

## Runtime data and output

- Input: `/app/benchmark/`, copied from the official `benchmark.zip` test input.
- Output: `/saisresult/result.zip`.
- Required zip members: `result.csv` and `result.log`.

The benchmark contains test inputs only. The image must not contain active or
inactive labels, EF evaluators, answer tables, precomputed rankings, or any
file that can directly recover final results.

## Code layout in image

- `/app/run.sh`: unique evaluation entrypoint.
- `/app/submit/`: runner, packer, and track dispatch code.
- `/app/submit/tracks/drugclip_agent/`: DrugClip scoring and hybrid ranking agent.
- `/app/agent/`: shared agent conventions and audit notes.
- `/app/agent_code/`: audit copy of agent code and this README.

## Model and ranking workflow

The audit-safe default mode does not download or package DUD-E/LIT-PCBA
benchmark-specific weights. It uses deterministic fingerprint, pocket, and QED
features for hybrid ranking. Neural retrieval can be enabled only with
externally reviewed, non-label-leaking weights. The agent logs the chosen
strategy, data paths, task count, scoring steps, and output packaging so the run
can be audited.

## Data processing and leakage control

The agent reads only the packaged benchmark inputs. It does not download DUD-E
or LIT-PCBA labels, does not query task labels, and does not use an EF feedback
loop for model or hyperparameter selection. Any allowed external data must be
generic pretraining or open-source model assets, not target-specific answer
libraries.

## Environment

- Base image: PyTorch CUDA runtime.
- Key Python packages: `torch`, `rdkit`, `biopandas`, `numpy`, `lmdb`, `tqdm`,
  `pyyaml`, `ipython`.
- GPU is not required for the audit-safe hybrid ranking path.

## Reproduction

Inside the image:

```bash
FUSAI_TRACK=drugclip SAISDATA=/saisdata SAISRESULT=/saisresult sh /app/run.sh
```

Expected artifact:

```text
/saisresult/result.zip
```

## External services and API keys

Current implementation does not require an LLM service for the default run.
If a future version enables an LLM, configure these environment variables:

- `LLM_API_KEY`: API key location.
- `LLM_BASE_URL`: provider base URL.
- `LLM_PROVIDER`: provider name.

Do not hard-code personal secrets in source code.

## Runtime notes

Expected runtime depends on the number of benchmark tasks. The run should be
non-interactive and deterministic apart from ordinary numerical differences.
