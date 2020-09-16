# HECSS Examples

This is a simple example of 3C-SiC crystal to use for testing.
This directory contains all files required to test and learn HECSS.

## Directories:

### VASP_3C-SiC

This directory is for learning/testing with VASP, which is more complicated and requires non-free VASP calculator and proper setup.
- 1x1x1 - crystalographic unit cell for quick tests
- 2x2x2 - 2x2x2 supercell for better quality, but slower, tests
- phon - directory for phonon calculations (contains path and born files)

#### Usage

1. Copy one of sc directories (sc_1x1x1 recommended for starters) to sc directory *above* the main hecss directory (i.e. two directories up).
2. Copy the phon directory to the same place (i.e. *above* the main hecss directory).
3. Open run_sampler.py as notebook in jupyterlab and set `base_dir` to `..`.
4. Set `T_goal` to desired temperature
5. Check the `run-vasp` script for the vasp running setup
5. Run the notebook
6. You can monitor calculations by opening `monitor_stats.py` and `monitor_phonons.py` 
   scripts in jupyterlab as notebooks


### LAMMPS_3C-SiC

This directory uses ASAP3/LAMMPS effective potential codes as a forces calculator.
Use of this directory requires no non-free components. The results are less accurate but you can calculate much larger systems and do it much faster. ASAP3 can be installed from conda or pypi:
```
conda install -c jochym asap3
```

#### Usage


