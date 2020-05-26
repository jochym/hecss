# HECSS

## High Efficiency Configuration Space Sampler

This is a Markow-Chain Metropolis-Hastings configuration space sampler.

The main sampler is in the `hecss.py` module. The calculation monitoring
functions are in the `calc_monitor.py` module. The examples are in:

* `run_sampler.py` - jupyter notebook with full sampler run example
* `monitor_stats.py` - sampling statistics notebook
* `monitor_phonons.py` - phonon convergence monitoring notebook
* `example` - directory with input data files with 3C-SiC 2x2x2 supercell

The notebooks should be opened with `open as -> notebook` in JupyterLab.

## Install

For now the install is only with `git clone`. The proper package is comming soon.
Run:
```
git clone http://git.dx.ifj.edu.pl/jochym/hecss.git 
```
in your working directory. It will create `hecss` directory with multiple files 
and `WORK` subdirectory. Do all your work in this directory (copy examples there 
and work from there). It is best to run calculations *above* the `hecss` directory
and keep notebooks controlling the calculations in the `WORK` directory:
```
--crystal---hecss---WORK
          |
          --calc_1---calc
          |        |
          |        --phon
          |        |
          |        --sc
          |
          --calc_2---calc
                   |
                   --phon
                   |
                   --sc
```
Alternatively you can have `calc_x` directories under `WORK` subdirectory. This structure enables you to update the package without touching your files.

## Update

If you followed above advice the update is done by executing:
```
git pull
```
from within `hecss` directory. This will pull all released updates for the package.

## Usage

Start by copying files from `example` subdirectory into `WORK` and following
the tutorial included there by opening `run_sampler.py` as Notebook.
