# AI notes

Snapshot of project context and workflow to resume later.

## Project state
- Branch: `AG` (no commits ahead of `origin/AG`; all changes are in the working tree).
- Source of truth: nbdev notebooks under `nbs/`; library code and docs are generated from them.
- Tests: `conda run -n hecss-dev nbdev_test` passes for unflagged and `--flags asap,quick`. `--flags vasp` not run (missing local VASP/ASE config).
- `vasp_ase` smoke test (`nbs/98_ase_smoketest.ipynb`) passes when `VASP_PP_PATH` is set (e.g., `VASP_PP_PATH=$(pwd)/local/vasp_pp conda run -n hecss-dev nbdev_test --flags vasp_ase --path nbs/98_ase_smoketest.ipynb`).

## Key files/scripts
- `run-calc.sh`: universal VASP entrypoint; delegates to `example/scripts/run-calc-ssh.sh`.
- `example/scripts/run-calc-ssh.sh`: supports local/remote execution; config precedence now includes `./run-calc.conf`, `~/.hecss/run-calc.conf`, `~/run-calc.conf`, script-adjacent.
- `TMP/sc/`: example calculation inputs and sample `run-calc.conf`.
- `nbs/90_Development.ipynb`: developer notes (runner config, direnv, local POTCAR storage, ASE smoke test pointer).
- `nbs/98_ase_smoketest.ipynb`: one-time ASE/VASP smoke test (rattle atoms, write inputs to `TMP`, run `run-calc.sh` via ASE `get_potential_energy`).

## nbdev workflow
- Edit notebooks in `nbs/`.
- Generate code/docs with `conda run -n hecss-dev nbdev_export` (and related nbdev commands).
- Tests live in notebooks with flags (e.g., `#| vasp`); run via `conda run -n hecss-dev nbdev_test [--flags ...]`.

## VASP runner config
- Provide `run-calc.conf` in one of:
  1) working directory (preferred),
  2) `~/.hecss/run-calc.conf` (user defaults),
  3) `~/run-calc.conf` (legacy),
  4) alongside `example/scripts/run-calc-ssh.sh`.
- `run-calc.sh` must be executable; `run-calc-ssh.sh` is executable.

## Local pseudopotentials (direnv)
- Store non-redistributable POTCAR trees in `local/vasp_pp/` (git-ignored).
- Use `direnv` to scope `VASP_PP_PATH` to this repo. Example `.envrc` (git-ignored):
  ```
  export VASP_PP_PATH=$PWD/local/vasp_pp
  ```
- Enable once in repo root: `direnv allow`.
- Without direnv, set explicitly per run, e.g.:
  ```
  VASP_PP_PATH=$(pwd)/local/vasp_pp conda run -n hecss-dev nbdev_test --flags vasp_ase --path nbs/98_ase_smoketest.ipynb
  ```

## Outstanding / next actions
- Install/configure direnv, add `.envrc`, and ensure `local/vasp_pp/` is populated.
- After VASP/ASE config is ready, run:
  - `conda run -n hecss-dev nbdev_test --flags vasp` (and other relevant flags if needed).
  - Optionally run `nbs/98_ase_smoketest.ipynb` to validate ASE integration.
- Keep developer-facing guidance in `nbs/90_Development.ipynb`; other notebooks point there.

## How to resume quickly
- Ensure conda env `hecss-dev` active (or use `conda run -n hecss-dev ...`).
- If using direnv: verify hook installed in shell; in repo root run `direnv allow` (once per trust).
- For VASP tests: have `run-calc.conf` available per precedence and `run-calc.sh` executable.

## User notes (preferences/context)
- Communication: user writes in Polish; responses in English; code/comments/docstrings in English.
- Style: concise, fact-based, practical; no fluff.
- Background: experienced Linux admin/programmer; physics (computational solid-state, phonons, DFT, anharmonicity), Python primary, C/C++ experienced; prefers open/free solutions.
- Constraints: moderate budget; avoid proprietary unless necessary.
- Project goal: experimental branch of HECSS (nbdev, notebooks in `nbs`), aiming to get tests passing in the new structure and support remote VASP execution via `run-calc.sh`.


