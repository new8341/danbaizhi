# Baxiangfenzi Agent Code README

## Overall approach

This image runs the targeted molecule design and retrosynthesis agent from
`/app/run.sh`. The entrypoint dispatches to
`submit.tracks.baxiangfenzi.BaxiangfenziRunner`, which reads the mounted target
PDB files, generates candidate molecules, scores/docks candidates, proposes a
route, and writes one CSV per target.

## Runtime data and output

- Input: `/saisdata/37/target1.pdb`, `/saisdata/37/target2.pdb`,
  `/saisdata/37/target3.pdb`.
- B-board note: these file names stay the same, but their contents may change.
- Output: `/saisresult/result.zip`.
- Required zip members: `result1.csv`, `result2.csv`, `result3.csv`.

The agent must generate results during container execution. The image must not
contain fixed target answers, hard-coded B-board information, or a hidden
molecule/route answer bank.

## Code layout in image

- `/app/run.sh`: unique evaluation entrypoint.
- `/app/submit/`: runner, packer, and track dispatch code.
- `/app/submit/tracks/baxiangfenzi_agent/`: molecule generation, filtering,
  docking, and route proposal code.
- `/app/Code/main.py`: audit entry copy of the track runner.
- `/app/Code/README.md`: audit copy of this reproduction README.
- `/app/Code/`: audit copy of the inference code.
- `/app/Reference/`: audit notes and shared conventions.
- `/app/agent_code/README.md`: this reproduction README.

## Model and design workflow

The current pipeline combines rule-based candidate generation, RDKit molecular
filters, docking with AutoDock Vina, and simple retrosynthesis route templates.
The agent logs target paths, generation settings, selected candidate, and route
construction information.

## Data processing

The mounted PDB target is parsed at runtime. Candidate molecules are generated
from generic medicinal-chemistry transformations and filtered by portable
properties. The B-board target replacement is handled by reading the mounted
files each run instead of relying on cached target-specific results.

## Environment

- Base image: Python 3.10 slim.
- System packages: `autodock-vina`, `openbabel`.
- Python packages: `rdkit`, `numpy`.

## Reproduction

Inside the image:

```bash
FUSAI_TRACK=baxiangfenzi SAISDATA=/saisdata SAISRESULT=/saisresult sh /app/run.sh
```

Expected artifact:

```text
/saisresult/result.zip
```

## External services and API keys

This semifinal image requires LLM/API key configuration at runtime. Configure:

- `LLM_API_KEY`: API key location.
- `LLM_BASE_URL`: provider base URL.
- `LLM_PROVIDER`: provider name.

Do not hard-code personal secrets in source code.

## Runtime notes

Primary runtime controls:

- `BAXIANG_MAX_CANDIDATES`
- `BAXIANG_MAX_DOCK`
- `BAXIANG_VINA_EXHAUSTIVENESS`
- `BAXIANG_SELECT_POOL`

The pipeline should be portable to a clean container with the mounted PDB files.
