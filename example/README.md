# Example directory

This is a simple example of 3C-SiC crystal to use for testing.
This directory contains all files required to test and learn HECSS.

## Directories:

- sc_1x1x1 - crystalographic unit cell for quick tests
- sc_2x2x2 - 2x2x2 supercell for better quality, but slower, tests
- phon - directory for phonon calculations (contains path and born files)

## How to use

1. Copy one of sc directories (sc_1x1x1 recommended for starters) to sc directory 
*above* the main hecss directory (i.e. two directories up).
2. Copy the phon directory to the same place (i.e. *above* the main hecss directory).
3. Open run_sampler.py as notebook in jupyterlab and set `base_dir` to `..`.
4. Set `T_goal` to desired temperature
5. Check the `run-vasp` script for the vasp running setup
5. Run the notebook
6. You can monitor calculations by opening `monitor_stats.py` and `monitor_phonons.py` 
   scripts in jupyterlab as notebooks

