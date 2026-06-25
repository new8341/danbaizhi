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
- `/app/submit/tracks/drugclip_agent/`: DrugClip structure-reference consensus agent.
- `/app/agent/`: shared agent conventions and audit notes.
- `/app/agent_code/`: audit copy of agent code and this README.

## Model and ranking workflow

The current image uses `structure_reference_consensus_v1`, rebuilt from the
official contestant benchmark contract. It does not download benchmark-specific
weights and does not reuse the previous hybrid/neural ranking code path. For
each task, the agent reads `task.json`, receptor files, co-crystal reference
ligands, and `ligands.csv` at runtime. It computes a deterministic consensus
score from Morgan fingerprint similarity, MACCS similarity, reference-ligand
descriptor fit, QED, and a generic receptor-complexity prior. The agent logs
the strategy design, rejected oracle/label paths, task-level inference counts,
score ranges, and final packaging.

## Data processing and leakage control

The agent reads only the packaged benchmark inputs. It does not download DUD-E
or LIT-PCBA labels, does not query task labels, does not carry an EF evaluator,
and does not use an EF feedback loop for model or hyperparameter selection. It
does not hard-code task IDs, ligand IDs, row order, known labels, or
target-specific answer rules.

## Environment

- Base image: PyTorch CUDA runtime.
- Key Python packages: `torch`, `rdkit`, `numpy`, `tqdm`, `pyyaml`.
- GPU is not required for the audit-safe structure-reference consensus path.

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

This semifinal image requires an API key to be available in the runtime
environment for audit and LLM-assisted extensions. Configure:

- `LLM_API_KEY` or `OPENAI_API_KEY`: API key location. In ACR builds this may
  be injected through the `OPENAI_API_KEY` Docker build argument.
- `LLM_BASE_URL` or `OPENAI_BASE_URL`: provider base URL. Defaults to
  `https://api.openai.com/v1`.
- `LLM_PROVIDER`: provider name. Defaults to `openai`.

Runtime logs show only a masked key prefix/suffix, not the full secret.

## Runtime notes

Expected runtime depends on the number of benchmark tasks. The run should be
non-interactive and deterministic apart from ordinary numerical differences.
