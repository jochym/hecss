# HECSS
> High Efficiency Configuration Space Sampler


[![PVersion Badge](https://img.shields.io/pypi/v/hecss.svg)](https://pypi.org/project/hecss/)
[![PDownloads Badge](https://img.shields.io/pypi/dm/hecss.svg)](https://pypi.org/project/hecss/)
[![CVersion Badge](https://anaconda.org/conda-forge/hecss/badges/version.svg)](https://anaconda.org/conda-forge/hecss)
[![Downloads Badge](https://anaconda.org/conda-forge/hecss/badges/downloads.svg)](https://anaconda.org/conda-forge/hecss)
[![License Badge](https://anaconda.org/jochym/hecss/badges/license.svg)](https://anaconda.org/jochym/hecss)

HECSS is a Markow chain Monte-Carlo, configuration space sampler using Metropolis-Hastings algorithm for probablity distribution sampling. It provides an alternative way to create representations of systems at thermal equilibrium without running a very expensive molecular dynamics simulation. The theoretical foundation of the code are presented in [SciPost Phys. 10, 129 (2021)](https://scipost.org/SciPostPhys.10.6.129) (short excerpt in [Background](https://jochym.gitlab.io/hecss/Background) in the [Documentation](https://jochym.gitlab.io/hecss/)). More detailed examples are included in the [LAMMPS](https://jochym.gitlab.io/hecss/LAMMPS_Tutorial) and [VASP](https://jochym.gitlab.io/hecss/VASP_Tutorial) tutorials.

If you use this software in published research please cite the above paper ([BibTeX](https://gitlab.com/jochym/hecss/-/raw/master/scipost.bib)) in your publication.

## A very short example

Minimal example using LAMMPS potential from the asap3 package and OpenKIM database. Here we will sample the thermodynamic distribution of 3C-SiC crystal at 300K. We start by importing required modules, define the crystal and energy/forces calculator, run the sampler and finally plot the energy distribution. 

```python
#asap
from ase.build import bulk
import asap3
from hecss.core import HECSS, select_asap_model
from hecss.monitor import plot_stats
```

Then we define the crystal and interaction model used in the calculation. In this case we use 3x3x3 supercell of the SiC crystal in zincblende structure and describe the interaction using LAMMPS potential from the OpenKIM database and ASAP3 implementation of the calculator.

```python
#asap
# model = 'Tersoff_LAMMPS_ErhartAlbe_2005_SiC__MO_903987585848_003'
model = select_asap_model('SiC')
cryst = bulk('SiC', crystalstructure='zincblende', a=4.38120844, cubic=True).repeat((3,3,3))
cryst.set_calculator(asap3.OpenKIMcalculator(model))
```

Then we define the sampler parameters (N -- number of samples, T -- temperature) and run it.

```python
#asap
T = 300
N = 1_000
samples = HECSS(cryst, asap3.OpenKIMcalculator(model), T).generate(N)
```

And finally we plot the histogram of the resulting energy distribution which corresponds to the thermal equilibrium distribution.

```python
#asap
plot_stats(samples, T)
```


    
![png](docs/images/output_9_0.png)
    


## Install

The HECSS package is avaliable on pypi and conda-forge additionally the package is present also in my personal anaconda channel (jochym). Installation is simple, but requires a number of other packages to be installed as well. Package menagers handle these dependencies automatically. 

### Install with pip
It is advisable to install in a dedicated virtual environment e.g.:
```
python3 -m venv venv
. venv/bin/activate
```
then install with `pip`:
```
pip install hecss
```

### Install with conda
Also installation with conda should be performed for dedicated or some other non-base environment. To create dedicated environment you can invoke `conda create`:
```
conda create -n hecss -c conda-forge hecss
```
or you can install in some working environment `venv`:
```
conda install -n venv -c conda-forge hecss
```

### Example data archive

The example subdirectory from the source may be downloaded directly from the source repository: [hecss-examples.zip](https://gitlab.com/jochym/hecss/-/archive/master/hecss-master.zip?path=example) 

### The source code

The source is published at the [Gitlab hecss repository](https://gitlab.com/jochym/hecss). 
You can access it with git (recommended, particularly if you want to contribute to the development):
```bash
git clone https://gitlab.com/jochym/hecss.git
```
or you can download the whole distribution as a zip archive: [hecss.zip](https://gitlab.com/jochym/hecss/-/archive/master/hecss-master.zip)
